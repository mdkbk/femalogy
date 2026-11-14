from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User, UserSession
from app.security import token_hash


def aware(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; everything here is UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def session_token(request: Request) -> str | None:
    """The web app sends an httpOnly cookie; the mobile app sends 'Authorization: Bearer <token>'."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(get_settings().session_cookie)


def current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    token = session_token(request)
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash(token))) if token else None
    if not sess or aware(sess.expires_at) <= datetime.now(UTC):
        if sess:
            db.delete(sess)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in again")
    return sess


def current_user(sess: UserSession = Depends(current_session)) -> User:
    return sess.user
