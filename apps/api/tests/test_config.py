import pytest
from pydantic import ValidationError

from gestion_boutiques.config import Settings


def test_development_allows_vite_loopback_origins() -> None:
    settings = Settings(_env_file=None)

    assert settings.allowed_cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_render_configuration_normalizes_database_and_cors_urls() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://app:secret@database.internal/app",
        cors_origin="https://gestion-boutiques.onrender.com/",
    )

    assert settings.database_url == (
        "postgresql+asyncpg://app:secret@database.internal/app"
    )
    assert settings.allowed_cors_origins == ["https://gestion-boutiques.onrender.com"]


def test_production_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL de production"):
        Settings(
            environment="production",
            database_url=(
                "postgresql+asyncpg://gestion_boutiques:change-me@localhost/gestion_boutiques"
            ),
            jwt_secret_key="short",
        )


def test_production_rejects_documented_example_placeholders() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL de production"):
        Settings(
            environment="production",
            database_url=(
                "postgresql+asyncpg://gestion_boutiques:CHANGE_ME@database/gestion_boutiques"
            ),
            jwt_secret_key="CHANGE_ME_WITH_AT_LEAST_32_RANDOM_CHARACTERS",
            cors_origin="https://gestion-boutiques.example.com",
        )


def test_production_accepts_explicit_secrets() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+asyncpg://app:secure-password@db.example.com/app",
        jwt_secret_key="a-production-secret-with-32-characters-minimum",
        cors_origin="https://gestion-boutiques.example.com",
    )

    assert settings.environment == "production"


def test_production_rejects_loopback_cors_origin() -> None:
    with pytest.raises(ValidationError, match="origines CORS de production"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://app:secure-password@db.example.com/app",
            jwt_secret_key="a-production-secret-with-32-characters-minimum",
        )