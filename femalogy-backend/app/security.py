"""Passwords, session tokens and keyed hashes.

- Passwords: Argon2id (the current OWASP recommendation), rehashed when parameters change.
- Sessions: a random 256-bit token lives only in the user's cookie (or the mobile app's
  secure storage). The database keeps just its SHA-256 hash, so a database leak can't be
  used to log in, and a session can be revoked by deleting its row.
- Login-attempt records store keyed hashes of the email and IP, never the values themselves.
"""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()

# A short list of the most common passwords; the length rule catches the rest.
COMMON_PASSWORDS = {
    "password", "password1", "password12", "password123", "password1234", "12345678", "123456789",
    "1234567890", "qwertyuiop", "qwerty123", "iloveyou", "iloveyou1", "11111111", "00000000",
    "abc12345", "abcd1234", "letmein1", "welcome1", "welcome123", "sunshine", "princess", "princess1",
    "football", "baseball", "monkey123", "dragon123", "superman", "trustno1", "passw0rd", "p@ssw0rd",
    "femalogy", "femalogy1", "femalogy123",
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def password_problem(password: str, email: str) -> str | None:
    p = password.strip().lower()
    if p in COMMON_PASSWORDS:
        return "That password is too common. Pick something harder to guess."
    if p == email.strip().lower() or p == email.split("@")[0].lower():
        return "Your password can't be your email."
    if len(set(p)) < 4:
        return "That password is too easy to guess. Use a mix of characters."
    return None


def new_session_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def keyed_hash(value: str) -> str:
    """HMAC so stored emails/IPs can be matched for rate limiting but not read back."""
    return hmac.new(get_settings().secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()
