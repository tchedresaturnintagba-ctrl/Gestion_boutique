from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from gestion_boutiques.api.dependencies import (
    CurrentUser,
    SessionDependency,
    SettingsDependency,
    authentication_error,
)
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.models.user import User
from gestion_boutiques.schemas.auth import CurrentUserResponse, LoginRequest, RefreshRequest
from gestion_boutiques.security.tokens import (
    InvalidTokenError,
    TokenPair,
    TokenType,
    create_token_pair,
    decode_token,
)
from gestion_boutiques.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenPair)
async def login(
    request: LoginRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenPair:
    user = await authenticate_user(
        session,
        organization_slug=request.organization_slug,
        email=str(request.email),
        password=request.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organisation, email ou mot de passe incorrect",
        )
    return create_token_pair(user, settings)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    request: RefreshRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenPair:
    try:
        payload = decode_token(
            request.refresh_token,
            expected_type=TokenType.REFRESH,
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
    if user is None or user.token_version != payload.token_version:
        raise authentication_error()
    return create_token_pair(user, settings)


@router.get("/me", response_model=CurrentUserResponse)
async def read_current_user(current_user: CurrentUser) -> User:
    return current_user


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    session: SessionDependency,
    current_user: CurrentUser,
) -> Response:
    current_user.token_version += 1
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)