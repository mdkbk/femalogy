import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import current_session, current_user
from app.config import get_settings
from app.db import get_db
from app.models import CheckIn, LoginAttempt, User, UserSession
from app.schemas import ProfileIn, ProfileOut, RegisterIn, SessionOut
from app.security import (
    hash_password,
    keyed_hash,
    needs_rehash,
    new_session_token,
    password_problem,
    token_hash,
    verify_password,
)

router = APIRouter(tags=["auth"])

# Rate limits (rolling windows). Tuned to stop guessing, not to annoy someone who mistypes.
WINDOW = timedelta(minutes=15)
MAX_FAILS_PER_EMAIL = 5
MAX_FAILS_PER_IP = 20
MAX_SIGNUPS_PER_IP_HOUR = 10
# The mobile app (later) asks for the token in the response body; the web app never sees it.
APP_CLIENT_HEADER = "x-femalogy-client"

# Same work as a real check, so "no such email" and "wrong password" take the same time.
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _now() -> datetime:
    return datetime.now(UTC)


def _count(db: Session, **where) -> int:
    q = select(func.count()).select_from(LoginAttempt).where(LoginAttempt.created_at >= where.pop("since"))
    for k, v in where.items():
        q = q.where(getattr(LoginAttempt, k) == v)
    return db.scalar(q) or 0


def _record(db: Session, kind: str, ip_h: str, email_h: str | None, success: bool) -> None:
    db.add(LoginAttempt(kind=kind, ip_hash=ip_h, email_hash=email_h, success=success))
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < _now() - timedelta(days=1)))
    db.commit()


def _too_many() -> HTTPException:
    return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                         "Too many attempts. Please wait 15 minutes and try again.")


def _start_session(db: Session, user: User, request: Request, response: Response) -> SessionOut:
    s = get_settings()
    token = new_session_token()
    db.add(UserSession(user_id=user.id, token_hash=token_hash(token),
                       expires_at=_now() + timedelta(days=s.session_days)))
    # tidy up this user's expired sessions
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < _now()))
    db.commit()
    if request.headers.get(APP_CLIENT_HEADER) == "app":
        return SessionOut(ok=True, access_token=token)
    response.set_cookie(
        s.session_cookie, token, max_age=s.session_days * 86400, httponly=True,
        secure=s.is_production, samesite="lax", path="/",
    )
    return SessionOut(ok=True)


@router.post("/auth/register", response_model=SessionOut, response_model_exclude_none=True, status_code=201)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip_h = keyed_hash(_ip(request))
    if _count(db, since=_now() - timedelta(hours=1), kind="register", ip_hash=ip_h) >= MAX_SIGNUPS_PER_IP_HOUR:
        raise _too_many()
    if not body.consent:
        raise HTTPException(422, "Please agree to how Femalogy stores your health data to create an account.")
    email = body.email.lower()
    problem = password_problem(body.password, email)
    if problem:
        raise HTTPException(422, problem)
    _record(db, "register", ip_h, None, True)
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "That email already has an account. Try signing in.")
    user = User(email=email, password_hash=hash_password(body.password), display_name=body.display_name,
                consented_at=_now())
    db.add(user)
    db.commit()
    return _start_session(db, user, request, response)


@router.post("/auth/login", response_model=SessionOut, response_model_exclude_none=True)
def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    email = username.strip().lower()
    ip_h, email_h = keyed_hash(_ip(request)), keyed_hash(email)
    since = _now() - WINDOW
    if (_count(db, since=since, kind="login", success=False, email_hash=email_h) >= MAX_FAILS_PER_EMAIL
            or _count(db, since=since, kind="login", success=False, ip_hash=ip_h) >= MAX_FAILS_PER_IP):
        raise _too_many()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        ok = verify_password(password, user.password_hash)
    else:
        verify_password(password, _DUMMY_HASH)  # same time cost, so timing can't reveal which emails exist
        ok = False
    _record(db, "login", ip_h, email_h, ok)
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return _start_session(db, user, request, response)


@router.post("/auth/logout", status_code=204)
def logout(response: Response, sess: UserSession = Depends(current_session), db: Session = Depends(get_db)):
    db.delete(sess)
    db.commit()
    response.delete_cookie(get_settings().session_cookie, path="/")


@router.post("/auth/logout-everywhere", status_code=204)
def logout_everywhere(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Signs out every device, e.g. after a lost phone."""
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
    response.delete_cookie(get_settings().session_cookie, path="/")


@router.get("/me", response_model=ProfileOut)
def me(user: User = Depends(current_user)):
    return user


@router.put("/me", response_model=ProfileOut)
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    return user


@router.get("/me/export")
def export_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Everything Femalogy stores about her, as a JSON download (GDPR access and portability)."""
    checkins = db.scalars(select(CheckIn).where(CheckIn.user_id == user.id).order_by(CheckIn.day)).all()
    data = {
        "exported_at": _now().isoformat(),
        "profile": {"email": user.email, "display_name": user.display_name,
                    "avg_cycle_length": user.avg_cycle_length, "avg_period_length": user.avg_period_length,
                    "created_at": user.created_at.isoformat(),
                    "consented_at": user.consented_at.isoformat() if user.consented_at else None},
        "periods": [{"start_date": str(p.start_date), "end_date": str(p.end_date) if p.end_date else None,
                     "gap_confirmed": p.gap_confirmed} for p in user.periods],
        "checkins": [{"day": str(c.day), "mood": c.mood, "energy": c.energy, "sleep_quality": c.sleep_quality,
                      "symptoms": c.symptoms, "notes": c.notes, "phase_at_checkin": c.phase_at_checkin}
                     for c in checkins],
    }
    return Response(json.dumps(data, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="femalogy-my-data.json"'})


@router.delete("/me", status_code=204)
def delete_me(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Deletes the account and every period, check-in and session with it."""
    db.delete(user)
    db.commit()
    response.delete_cookie(get_settings().session_cookie, path="/")
