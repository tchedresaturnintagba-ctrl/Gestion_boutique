import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from gestion_boutiques.config import get_settings
from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.main import app
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.store import Store, StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import create_token_pair

pytestmark = pytest.mark.integration


def test_store_management_and_owner_visibility() -> None:
    async def scenario() -> None:
        organization_id = uuid4()
        manager = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"manager-{uuid4()}@example.com",
            full_name="Store Manager",
            password_hash="unused",
            role=UserRole.MANAGER,
        )
        owner = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"owner-{uuid4()}@example.com",
            full_name="Store Owner",
            password_hash="unused",
            role=UserRole.OWNER,
        )
        assigned_store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Assigned Store",
            code="ASSIGNED",
        )
        hidden_store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Hidden Store",
            code="HIDDEN",
        )

        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                session.add(
                    Organization(
                        id=organization_id,
                        name="Store API Test",
                        slug=f"stores-{uuid4()}",
                    )
                )
                session.add_all([manager, owner, assigned_store, hidden_store])
                session.add(StoreOwnership(store_id=assigned_store.id, owner_id=owner.id))

            settings = get_settings()
            manager_token = create_token_pair(manager, settings).access_token
            owner_token = create_token_pair(owner, settings).access_token
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                create_response = await client.post(
                    "/api/v1/stores",
                    headers={"Authorization": f"Bearer {manager_token}"},
                    json={"name": "New Store", "code": "new-01", "address": "Abidjan"},
                )
                assert create_response.status_code == 201
                assert create_response.json()["code"] == "NEW-01"

                owner_create_response = await client.post(
                    "/api/v1/stores",
                    headers={"Authorization": f"Bearer {owner_token}"},
                    json={"name": "Forbidden Store", "code": "NOPE"},
                )
                assert owner_create_response.status_code == 403

                owner_list_response = await client.get(
                    "/api/v1/stores",
                    headers={"Authorization": f"Bearer {owner_token}"},
                )
                assert owner_list_response.status_code == 200
                assert owner_list_response.json()["total"] == 1
                assert owner_list_response.json()["items"][0]["id"] == str(assigned_store.id)

                hidden_response = await client.get(
                    f"/api/v1/stores/{hidden_store.id}",
                    headers={"Authorization": f"Bearer {owner_token}"},
                )
                assert hidden_response.status_code == 404

                suspend_response = await client.post(
                    f"/api/v1/stores/{assigned_store.id}/suspend",
                    headers={"Authorization": f"Bearer {manager_token}"},
                )
                assert suspend_response.status_code == 204
        finally:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                await session.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            await engine.dispose()

    asyncio.run(scenario())