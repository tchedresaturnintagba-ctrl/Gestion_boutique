from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestion Boutiques API"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
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

    @model_validator(mode="after")
    def reject_development_secrets_in_production(self) -> "Settings":
        if self.environment != "production":
            return self
        if "change-me" in self.database_url.lower():
            raise ValueError("L'URL PostgreSQL de production doit être configurée")
        secret = self.jwt_secret_key.get_secret_value()
        if secret == "change-this-development-secret" or len(secret) < 32:
            raise ValueError("La clé JWT de production doit contenir au moins 32 caractères")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()