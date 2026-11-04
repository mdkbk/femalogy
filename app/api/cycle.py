from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.api.guide import build_guide
from app.cycle.engine import CycleSettings, compute_status, phase_calendar
from app.db import get_db
from app.knowledge.loader import knowledge
from app.models import CheckIn, Period, User
from app.schemas import CheckInIn, CheckInOut, PeriodIn, PeriodOut, RedFlag, TodayOut

router = APIRouter(tags=["cycle"])

# the server may be a day behind the user's timezone, so allow "tomorrow" in server time
DATE_TOLERANCE = timedelta(days=1)


def _not_future(day: date, what: str) -> None:
    if day > date.today() + DATE_TOLERANCE:
        raise HTTPException(422, f"Can't log {what} in the future")


def _status_for(user: User, today: date):
    periods = [p for p in user.periods if p.start_date <= today]
    if not periods:
        return None
    lengths = [(p.end_date - p.start_date).days + 1 for p in periods if p.end_date]
    settings = CycleSettings(user.avg_cycle_length, user.avg_period_length)
    return compute_status([p.start_date for p in periods], today, settings, lengths or None)


def _red_flags(triggers: set[str]) -> list[RedFlag]:
    return [RedFlag(id=r["id"], text=r["text"]) for r in knowledge()["red_flags"] if r["trigger"] in triggers]


# ---- periods ----

@router.post("/periods", response_model=PeriodOut, status_code=201)
def log_period(body: PeriodIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _not_future(body.start_date, "a period")
    period = Period(user_id=user.id, **body.model_dump())
    db.add(period)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(409, "A period already starts on that date") from err
    return period


@router.get("/periods", response_model=list[PeriodOut])
def list_periods(user: User = Depends(current_user)):
    return user.periods


@router.patch("/periods/{period_id}", response_model=PeriodOut)
def update_period(period_id: str, body: PeriodIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    period = db.get(Period, period_id)
    if not period or period.user_id != user.id:
        raise HTTPException(404, "Period not found")
    _not_future(body.start_date, "a period")
    period.start_date, period.end_date = body.start_date, body.end_date
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(409, "A period already starts on that date") from err
    return period


@router.delete("/periods/{period_id}", status_code=204)
def delete_period(period_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    period = db.get(Period, period_id)
    if not period or period.user_id != user.id:
        raise HTTPException(404, "Period not found")
    db.delete(period)
    db.commit()


# ---- today + calendar ----

@router.get("/today", response_model=TodayOut)
def today_view(
    on: date | None = Query(default=None, description="Defaults to today; handy for testing"),
    user: User = Depends(current_user),
):
    day = on or date.today()
    st = _status_for(user, day)
    if not st:
        raise HTTPException(409, "Log your last period start date first")
    guide = build_guide(st.phase.value)
    return TodayOut(
        date=day,
        cycle_day=st.cycle_day,
        phase=st.phase.value,
        phase_title=guide.title,
        cycle_length_estimate=st.cycle_length_estimate,
        ovulation_date_estimate=st.ovulation_date_estimate,
        next_period_estimate=st.next_period_estimate,
        days_until_next_period=st.days_until_next_period,
        confidence=st.confidence.value,
        complete_cycles_logged=st.complete_cycles_logged,
        flags=st.flags,
        red_flags=_red_flags(set(st.flags)),
        guide=guide,
        disclaimer=knowledge()["disclaimer"],
    )


@router.get("/calendar")
def calendar(
    days: int = Query(default=35, ge=1, le=120),
    on: date | None = Query(default=None, description="Start date; the app should send the user's local date"),
    user: User = Depends(current_user),
):
    st = _status_for(user, on or date.today())
    if not st:
        raise HTTPException(409, "Log your last period start date first")
    return [{"date": d, "phase": p.value} for d, p in phase_calendar(st, days)]


# ---- check-ins ----

@router.put("/checkins", response_model=CheckInOut)
def upsert_checkin(body: CheckInIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """One check-in per day; sending the same day again updates it."""
    _not_future(body.day, "a check-in")
    st = _status_for(user, body.day)
    existing = db.scalar(select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.day == body.day))
    checkin = existing or CheckIn(user_id=user.id, day=body.day)
    for k, v in body.model_dump().items():
        setattr(checkin, k, v)
    checkin.phase_at_checkin = st.phase.value if st else None
    db.add(checkin)
    db.commit()
    out = CheckInOut.model_validate(checkin)
    out.red_flags = _red_flags({f"symptom:{s}" for s in body.symptoms})
    return out


@router.get("/checkins", response_model=list[CheckInOut])
def list_checkins(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(CheckIn).where(CheckIn.user_id == user.id).order_by(CheckIn.day)).all()
