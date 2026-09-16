from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestion Boutiques API"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    cors_origin: str | None = None
    database_url: str = "postgresql+asyncpg://gestion_boutiques:change-me@127.0.0.1:5432/gestion_boutiques"
    jwt_secret_key: SecretStr = SecretStr("change-this-development-secret")
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="GB_",
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_asyncpg_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("cors_origin")
    @classmethod
    def normalize_cors_origin(cls, value: str | None) -> str | None:
        return value.rstrip("/") if value else None

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [self.cors_origin] if self.cors_origin else self.cors_origins

    @model_validator(mode="after")
    def reject_development_secrets_in_production(self) -> "Settings":
        if self.environment != "production":
            return self
        database_url = self.database_url.lower()
        if "change-me" in database_url or "change_me" in database_url:
            raise ValueError("L'URL PostgreSQL de production doit être configurée")
        secret = self.jwt_secret_key.get_secret_value()
        normalized_secret = secret.lower()
        if (
            secret == "change-this-development-secret"
            or "change-me" in normalized_secret
            or "change_me" in normalized_secret
            or len(secret) < 32
        ):
            raise ValueError("La clé JWT de production doit contenir au moins 32 caractères")
        for origin in self.allowed_cors_origins:
            parsed_origin = urlsplit(origin)
            if (
                parsed_origin.scheme != "https"
                or parsed_origin.hostname in {"localhost", "127.0.0.1"}
            ):
                raise ValueError("Les origines CORS de production doivent utiliser HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()