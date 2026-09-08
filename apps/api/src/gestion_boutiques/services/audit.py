from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.models.audit import AuditEvent


def record_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )