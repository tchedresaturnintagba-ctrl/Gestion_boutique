import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from gestion_boutiques.config import get_settings
from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.main import app
from gestion_boutiques.models.audit import AuditEvent
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.store import Store
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import create_token_pair

pytestmark = pytest.mark.integration


def test_cross_tenant_assignment_is_hidden_and_audit_is_immutable() -> None:
    async def scenario() -> None:
        organization_a_id = uuid4()
        organization_b_id = uuid4()
        manager = User(
            id=uuid4(),
            organization_id=organization_a_id,
            email=f"manager-{uuid4()}@example.com",
            full_name="Tenant A Manager",
            password_hash="unused",
            role=UserRole.MANAGER,
        )
        store = Store(
            id=uuid4(),
            organization_id=organization_a_id,
            name="Tenant A Store",
            code="TENANT-A",
        )
        foreign_owner = User(
            id=uuid4(),
            organization_id=organization_b_id,
            email=f"owner-{uuid4()}@example.com",
            full_name="Tenant B Owner",
            password_hash="unused",
            role=UserRole.OWNER,
        )
        event_id = uuid4()

        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_a_id)
                session.add(
                    Organization(
                        id=organization_a_id,
                        name="Tenant A",
                        slug=f"tenant-a-{uuid4()}",
                    )
                )
                session.add_all([manager, store])

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_b_id)
                session.add(
                    Organization(
                        id=organization_b_id,
                        name="Tenant B",
                        slug=f"tenant-b-{uuid4()}",
                    )
                )
                session.add(foreign_owner)

            manager_token = create_token_pair(manager, get_settings()).access_token
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/stores/{store.id}/owners/{foreign_owner.id}",
                    headers={"Authorization": f"Bearer {manager_token}"},
                )
                assert response.status_code == 404
                assert response.json()["detail"] == "Propriétaire introuvable"

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_a_id)
                session.add(
                    AuditEvent(
                        id=event_id,
                        organization_id=organization_a_id,
                        actor_user_id=manager.id,
                        action="original.action",
                        entity_type="store",
                        entity_id=store.id,
                    )
                )

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_a_id)
                result = await session.execute(
                    update(AuditEvent)
                    .where(AuditEvent.id == event_id)
                    .values(action="tampered.action")
                )
                assert result.rowcount == 0

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_a_id)
                event = await session.scalar(select(AuditEvent).where(AuditEvent.id == event_id))
                assert event is not None
                assert event.action == "original.action"
        finally:
            for organization_id in (organization_a_id, organization_b_id):
                async with async_session_factory() as session, session.begin():
                    await set_tenant_context(session, organization_id)
                    await session.execute(
                        delete(Organization).where(Organization.id == organization_id)
                    )
            await engine.dispose()

    asyncio.run(scenario())