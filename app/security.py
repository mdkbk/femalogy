from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: str) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm]).get("sub")
    except jwt.PyJWTError:
        return None
