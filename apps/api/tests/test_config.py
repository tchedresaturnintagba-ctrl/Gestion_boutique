import pytest
from pydantic import ValidationError

from gestion_boutiques.config import Settings


def test_production_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL de production"):
        Settings(
            environment="production",
            database_url=(
                "postgresql+asyncpg://gestion_boutiques:change-me@localhost/gestion_boutiques"
            ),
            jwt_secret_key="short",
        )


def test_production_accepts_explicit_secrets() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+asyncpg://app:secure-password@db.example.com/app",
        jwt_secret_key="a-production-secret-with-32-characters-minimum",
    )

    assert settings.environment == "production"