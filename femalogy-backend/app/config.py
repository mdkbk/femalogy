from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Femalogy API"
    # "production" turns on secure cookies, HSTS, hides /docs and enforces strong secrets
    env: str = "development"
    database_url: str = "postgresql+psycopg://femalogy:femalogy@localhost:5432/femalogy"
    # Server secret, used to key hashes of login-attempt data (emails/IPs are never stored in clear).
    # Older .env files call it JWT_SECRET; both names work.
    secret_key: str = Field(default="change-me", validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"))
    session_days: int = 30
    session_cookie: str = "femalogy_session"
    # Fernet key for encrypting check-in notes. Generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    field_encryption_key: str = ""
    # extra web origins allowed to call the API (local dev servers); the app's own origin is always allowed
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8081"
    # folder with the built web app (femalogy-web/dist); served at / when it exists
    web_dist: str = ""

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        # hosted Postgres (Neon, Render, Heroku-style) hands out postgres:// or postgresql:// URLs
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def startup_problems(s: Settings) -> list[str]:
    """Refuse to start with weak or missing secrets."""
    from cryptography.fernet import Fernet

    problems = []
    if len(s.secret_key) < 32 or s.secret_key in ("change-me", "replace-me"):
        problems.append("SECRET_KEY is missing or too short (use 32+ random characters)")
    try:
        Fernet(s.field_encryption_key.encode())
    except Exception:
        problems.append("FIELD_ENCRYPTION_KEY is missing or not a valid Fernet key")
    if s.is_production and s.database_url.startswith("sqlite"):
        problems.append("Production needs a real Postgres DATABASE_URL, not SQLite")
    return problems
