from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gestion_boutiques.api.dependencies import SessionDependency, require_roles
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.schemas.owners import (
    OwnerCreate,
    OwnerListResponse,
    OwnerPasswordReset,
    OwnerResponse,
    OwnerUpdate,
)
from gestion_boutiques.security.passwords import hash_password
from gestion_boutiques.services.audit import record_audit_event

router = APIRouter(prefix="/owners", tags=["owners"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]


def owner_response(owner: User) -> OwnerResponse:
    return OwnerResponse(
        id=owner.id,
        organization_id=owner.organization_id,
        email=owner.email,
        full_name=owner.full_name,
        role=owner.role,
        is_active=owner.is_active,
        store_ids=[ownership.store_id for ownership in owner.store_ownerships],
        created_at=owner.created_at,
        updated_at=owner.updated_at,
    )


async def get_owner(session: AsyncSession, manager: User, owner_id: UUID) -> User:
    owner = await session.scalar(
        select(User)
        .options(selectinload(User.store_ownerships))
        .where(
            User.id == owner_id,
            User.organization_id == manager.organization_id,
            User.role == UserRole.OWNER,
        )
    )
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propriétaire introuvable",
        )
    return owner


@router.post("", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
async def create_owner(
    request: OwnerCreate,
    session: SessionDependency,
    manager: ManagerUser,
) -> OwnerResponse:
    owner = User(
        organization_id=manager.organization_id,
        email=str(request.email),
        full_name=request.full_name,
        password_hash=hash_password(request.password),
        role=UserRole.OWNER,
    )
    session.add(owner)
    try:
        await session.flush()
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="owner.created",
            entity_type="user",
            entity_id=owner.id,
        )
        await session.refresh(owner)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email existe déjà dans l'organisation",
        ) from error
    return OwnerResponse(
        id=owner.id,
        organization_id=owner.organization_id,
        email=owner.email,
        full_name=owner.full_name,
        role=owner.role,
        is_active=owner.is_active,
        store_ids=[],
        created_at=owner.created_at,
        updated_at=owner.updated_at,
    )


@router.get("", response_model=OwnerListResponse)
async def list_owners(
    session: SessionDependency,
    manager: ManagerUser,
    search: Annotated[str | None, Query(max_length=160)] = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OwnerListResponse:
    query = select(User).where(
        User.organization_id == manager.organization_id,
        User.role == UserRole.OWNER,
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(User.full_name.ilike(term), User.email.ilike(term)))
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    owners = (
        await session.scalars(
            query.options(selectinload(User.store_ownerships))
            .order_by(User.full_name, User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return OwnerListResponse(
        items=[owner_response(owner) for owner in owners],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{owner_id}", response_model=OwnerResponse)
async def read_owner(
    owner_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> OwnerResponse:
    return owner_response(await get_owner(session, manager, owner_id))


@router.patch("/{owner_id}", response_model=OwnerResponse)
async def update_owner(
    owner_id: UUID,
    request: OwnerUpdate,
    session: SessionDependency,
    manager: ManagerUser,
) -> OwnerResponse:
    owner = await get_owner(session, manager, owner_id)
    changes = request.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(owner, field, value)
    try:
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="owner.updated",
            entity_type="user",
            entity_id=owner.id,
            details={"changed_fields": sorted(changes)},
        )
        await session.flush()
        await session.refresh(owner, attribute_names=["created_at", "updated_at"])
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email existe déjà dans l'organisation",
        ) from error
    return owner_response(owner)


async def change_owner_status(
    *,
    owner_id: UUID,
    is_active: bool,
    session: AsyncSession,
    manager: User,
) -> Response:
    owner = await get_owner(session, manager, owner_id)
    owner.is_active = is_active
    owner.token_version += 1
    record_audit_event(
        session,
        organization_id=manager.organization_id,
        actor_user_id=manager.id,
        action="owner.activated" if is_active else "owner.suspended",
        entity_type="user",
        entity_id=owner.id,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{owner_id}/suspend", status_code=status.HTTP_204_NO_CONTENT)
async def suspend_owner(
    owner_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    return await change_owner_status(
        owner_id=owner_id,
        is_active=False,
        session=session,
        manager=manager,
    )


@router.post("/{owner_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_owner(
    owner_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    return await change_owner_status(
        owner_id=owner_id,
        is_active=True,
        session=session,
        manager=manager,
    )


@router.post("/{owner_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_owner_password(
    owner_id: UUID,
    request: OwnerPasswordReset,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    owner = await get_owner(session, manager, owner_id)
    owner.password_hash = hash_password(request.new_password)
    owner.token_version += 1
    record_audit_event(
        session,
        organization_id=manager.organization_id,
        actor_user_id=manager.id,
        action="owner.password_reset",
        entity_type="user",
        entity_id=owner.id,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)