from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.api.dependencies import (
    CurrentUser,
    SessionDependency,
    require_roles,
)
from gestion_boutiques.models.store import Store, StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.schemas.stores import (
    StoreCreate,
    StoreListResponse,
    StoreResponse,
    StoreUpdate,
)
from gestion_boutiques.services.audit import record_audit_event

router = APIRouter(prefix="/stores", tags=["stores"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]


def accessible_stores_query(current_user: User):
    query = select(Store).where(Store.organization_id == current_user.organization_id)
    if current_user.role is UserRole.OWNER:
        query = query.join(StoreOwnership).where(StoreOwnership.owner_id == current_user.id)
    return query


async def get_accessible_store(
    session: AsyncSession,
    current_user: User,
    store_id: UUID,
) -> Store:
    store = await session.scalar(
        accessible_stores_query(current_user).where(Store.id == store_id)
    )
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boutique introuvable")
    return store


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    request: StoreCreate,
    session: SessionDependency,
    manager: ManagerUser,
) -> Store:
    store = Store(
        organization_id=manager.organization_id,
        name=request.name,
        code=request.code,
        address=request.address,
    )
    session.add(store)
    try:
        await session.flush()
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="store.created",
            entity_type="store",
            entity_id=store.id,
            details={"code": store.code},
        )
        await session.refresh(store)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce code de boutique existe déjà",
        ) from error
    return store


@router.get("", response_model=StoreListResponse)
async def list_stores(
    session: SessionDependency,
    current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=160)] = None,
    is_active: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> StoreListResponse:
    query = accessible_stores_query(current_user)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Store.name.ilike(term), Store.code.ilike(term)))
    if is_active is not None:
        query = query.where(Store.is_active.is_(is_active))

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    stores = (
        await session.scalars(
            query.order_by(Store.name, Store.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return StoreListResponse(
        items=[StoreResponse.model_validate(store) for store in stores],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{store_id}", response_model=StoreResponse)
async def read_store(
    store_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> Store:
    return await get_accessible_store(session, current_user, store_id)


@router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: UUID,
    request: StoreUpdate,
    session: SessionDependency,
    manager: ManagerUser,
) -> Store:
    store = await get_accessible_store(session, manager, store_id)
    changes = request.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(store, field, value)
    try:
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="store.updated",
            entity_type="store",
            entity_id=store.id,
            details={"changed_fields": sorted(changes)},
        )
        await session.flush()
        await session.refresh(store)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce code de boutique existe déjà",
        ) from error
    return store


async def change_store_status(
    *,
    store_id: UUID,
    is_active: bool,
    session: AsyncSession,
    manager: User,
) -> Response:
    store = await get_accessible_store(session, manager, store_id)
    store.is_active = is_active
    record_audit_event(
        session,
        organization_id=manager.organization_id,
        actor_user_id=manager.id,
        action="store.activated" if is_active else "store.suspended",
        entity_type="store",
        entity_id=store.id,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{store_id}/suspend", status_code=status.HTTP_204_NO_CONTENT)
async def suspend_store(
    store_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    return await change_store_status(
        store_id=store_id,
        is_active=False,
        session=session,
        manager=manager,
    )


@router.post("/{store_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
async def activate_store(
    store_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    return await change_store_status(
        store_id=store_id,
        is_active=True,
        session=session,
        manager=manager,
    )