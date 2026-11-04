from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Femalogy API"
    database_url: str = "postgresql+psycopg://femalogy:femalogy@localhost:5432/femalogy"
    jwt_secret: str = "change-me"  # set a long random value in .env
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    # Fernet key for encrypting check-in notes. Generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    field_encryption_key: str = ""
    # web frontends allowed to call the API, comma separated
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8081"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
