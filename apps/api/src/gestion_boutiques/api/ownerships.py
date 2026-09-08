from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select

from gestion_boutiques.api.dependencies import SessionDependency, require_roles
from gestion_boutiques.api.owners import get_owner
from gestion_boutiques.api.stores import get_accessible_store
from gestion_boutiques.models.store import StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.services.audit import record_audit_event

router = APIRouter(prefix="/stores", tags=["store ownerships"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]


@router.post(
    "/{store_id}/owners/{owner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_owner(
    store_id: UUID,
    owner_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    await get_accessible_store(session, manager, store_id)
    await get_owner(session, manager, owner_id)
    ownership = await session.scalar(
        select(StoreOwnership).where(
            StoreOwnership.store_id == store_id,
            StoreOwnership.owner_id == owner_id,
        )
    )
    if ownership is None:
        session.add(StoreOwnership(store_id=store_id, owner_id=owner_id))
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="store.owner_assigned",
            entity_type="store",
            entity_id=store_id,
            details={"owner_id": str(owner_id)},
        )
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{store_id}/owners/{owner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unassign_owner(
    store_id: UUID,
    owner_id: UUID,
    session: SessionDependency,
    manager: ManagerUser,
) -> Response:
    await get_accessible_store(session, manager, store_id)
    await get_owner(session, manager, owner_id)
    result = await session.execute(
        delete(StoreOwnership).where(
            StoreOwnership.store_id == store_id,
            StoreOwnership.owner_id == owner_id,
        )
    )
    if result.rowcount:
        record_audit_event(
            session,
            organization_id=manager.organization_id,
            actor_user_id=manager.id,
            action="store.owner_unassigned",
            entity_type="store",
            entity_id=store_id,
            details={"owner_id": str(owner_id)},
        )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)