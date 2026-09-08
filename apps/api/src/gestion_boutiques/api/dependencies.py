from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.config import Settings, get_settings
from gestion_boutiques.db.session import get_db_session
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import InvalidTokenError, TokenType, decode_token

bearer_scheme = HTTPBearer(auto_error=False)
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    session: SessionDependency,
    settings: SettingsDependency,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise authentication_error()
    try:
        payload = decode_token(
            credentials.credentials,
            expected_type=TokenType.ACCESS,
            settings=settings,
        )
    except InvalidTokenError as error:
        raise authentication_error() from error

    await set_tenant_context(session, payload.organization_id)
    user = await session.scalar(
        select(User).where(
            User.id == payload.subject,
            User.organization_id == payload.organization_id,
            User.is_active.is_(True),
        )
    )
    if (
        user is None
        or user.role is not payload.role
        or user.token_version != payload.token_version
    ):
        raise authentication_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], User]:
    async def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes",
            )
        return current_user

    return role_dependency