from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from gestion_boutiques.api.dependencies import SessionDependency, require_roles
from gestion_boutiques.models.audit import AuditEvent
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.schemas.audit import AuditEventListResponse, AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["audit"])
ManagerUser = Annotated[User, Depends(require_roles(UserRole.MANAGER))]


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    session: SessionDependency,
    manager: ManagerUser,
    action: Annotated[str | None, Query(max_length=80)] = None,
    entity_type: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditEventListResponse:
    query = select(AuditEvent).where(AuditEvent.organization_id == manager.organization_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)

    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    events = (
        await session.scalars(
            query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(event) for event in events],
        total=total or 0,
        page=page,
        page_size=page_size,
    )