from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

import jwt
from pydantic import BaseModel, ValidationError

from gestion_boutiques.config import Settings
from gestion_boutiques.models.user import User, UserRole

ALGORITHM = "HS256"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    subject: UUID
    organization_id: UUID
    role: UserRole
    token_type: TokenType
    token_version: int
    issued_at: datetime
    expires_at: datetime
    token_id: UUID


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class InvalidTokenError(ValueError):
    pass


def _encode_token(
    *,
    user: User,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings,
    now: datetime,
) -> str:
    payload = {
        "sub": str(user.id),
        "org": str(user.organization_id),
        "role": user.role.value,
        "typ": token_type.value,
        "ver": user.token_version,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=ALGORITHM,
    )


def create_token_pair(
    user: User,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> TokenPair:
    issued_at = now or datetime.now(UTC)
    access_delta = timedelta(minutes=settings.access_token_minutes)
    refresh_delta = timedelta(days=settings.refresh_token_days)
    return TokenPair(
        access_token=_encode_token(
            user=user,
            token_type=TokenType.ACCESS,
            expires_delta=access_delta,
            settings=settings,
            now=issued_at,
        ),
        refresh_token=_encode_token(
            user=user,
            token_type=TokenType.REFRESH,
            expires_delta=refresh_delta,
            settings=settings,
            now=issued_at,
        ),
        expires_in=int(access_delta.total_seconds()),
    )


def decode_token(
    token: str,
    *,
    expected_type: TokenType,
    settings: Settings,
) -> TokenPayload:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "org", "role", "typ", "ver", "iat", "exp", "jti"]},
        )
        payload = TokenPayload.model_validate(
            {
                "subject": claims["sub"],
                "organization_id": claims["org"],
                "role": claims["role"],
                "token_type": claims["typ"],
                "token_version": claims["ver"],
                "issued_at": claims["iat"],
                "expires_at": claims["exp"],
                "token_id": claims["jti"],
            }
        )
    except (jwt.InvalidTokenError, KeyError, ValidationError, ValueError) as error:
        raise InvalidTokenError("Jeton invalide ou expiré") from error

    if payload.token_type is not expected_type:
        raise InvalidTokenError("Type de jeton invalide")
    return payload