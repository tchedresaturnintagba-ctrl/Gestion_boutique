from uuid import UUID

import pytest

from gestion_boutiques.config import Settings
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.passwords import hash_password, verify_password
from gestion_boutiques.security.tokens import (
    InvalidTokenError,
    TokenType,
    create_token_pair,
    decode_token,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000002")


def build_user() -> User:
    return User(
        id=USER_ID,
        organization_id=ORGANIZATION_ID,
        email="manager@example.com",
        full_name="Gestionnaire Test",
        password_hash="unused",
        role=UserRole.MANAGER,
        token_version=2,
    )


def test_password_is_hashed_with_argon2id() -> None:
    password_hash = hash_password("a-secure-password")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("a-secure-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_contains_tenant_and_role() -> None:
    settings = Settings(jwt_secret_key="test-secret-with-at-least-32-characters")
    pair = create_token_pair(build_user(), settings)

    payload = decode_token(pair.access_token, expected_type=TokenType.ACCESS, settings=settings)

    assert payload.subject == USER_ID
    assert payload.organization_id == ORGANIZATION_ID
    assert payload.role is UserRole.MANAGER
    assert payload.token_version == 2
    assert (payload.expires_at - payload.issued_at).total_seconds() == 900
    assert pair.expires_in == 900


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    settings = Settings(jwt_secret_key="test-secret-with-at-least-32-characters")
    pair = create_token_pair(build_user(), settings)

    with pytest.raises(InvalidTokenError, match="Type de jeton invalide"):
        decode_token(pair.refresh_token, expected_type=TokenType.ACCESS, settings=settings)


def test_modified_token_is_rejected() -> None:
    settings = Settings(jwt_secret_key="test-secret-with-at-least-32-characters")
    token = create_token_pair(build_user(), settings).access_token
    modified_token = f"{token[:-2]}xx"

    with pytest.raises(InvalidTokenError, match="Jeton invalide ou expiré"):
        decode_token(modified_token, expected_type=TokenType.ACCESS, settings=settings)