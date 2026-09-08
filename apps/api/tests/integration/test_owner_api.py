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
from gestion_boutiques.models.store import Store
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import create_token_pair

pytestmark = pytest.mark.integration


def test_owner_lifecycle_and_store_assignment() -> None:
    async def scenario() -> None:
        organization_id = uuid4()
        organization_slug = f"owners-{uuid4()}"
        manager = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"manager-{uuid4()}@example.com",
            full_name="Owner Manager",
            password_hash="unused",
            role=UserRole.MANAGER,
        )
        store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Owner Store",
            code="OWNER-STORE",
        )
        owner_email = f"owner-{uuid4()}@example.com"
        initial_password = "initial-owner-password"
        new_password = "new-owner-password-2026"

        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                session.add(
                    Organization(
                        id=organization_id,
                        name="Owner API Test",
                        slug=organization_slug,
                    )
                )
                session.add_all([manager, store])

            manager_token = create_token_pair(manager, get_settings()).access_token
            manager_headers = {"Authorization": f"Bearer {manager_token}"}
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                create_response = await client.post(
                    "/api/v1/owners",
                    headers=manager_headers,
                    json={
                        "email": owner_email.upper(),
                        "full_name": "  Owner Test  ",
                        "password": initial_password,
                    },
                )
                assert create_response.status_code == 201
                owner = create_response.json()
                owner_id = owner["id"]
                assert owner["email"] == owner_email
                assert owner["full_name"] == "Owner Test"
                assert owner["store_ids"] == []

                duplicate_response = await client.post(
                    "/api/v1/owners",
                    headers=manager_headers,
                    json={
                        "email": owner_email,
                        "full_name": "Duplicate Owner",
                        "password": initial_password,
                    },
                )
                assert duplicate_response.status_code == 409

                assign_response = await client.post(
                    f"/api/v1/stores/{store.id}/owners/{owner_id}",
                    headers=manager_headers,
                )
                assert assign_response.status_code == 204

                detail_response = await client.get(
                    f"/api/v1/owners/{owner_id}",
                    headers=manager_headers,
                )
                assert detail_response.status_code == 200
                assert detail_response.json()["store_ids"] == [str(store.id)]

                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "organization_slug": organization_slug,
                        "email": owner_email,
                        "password": initial_password,
                    },
                )
                assert login_response.status_code == 200
                owner_token = login_response.json()["access_token"]
                owner_headers = {"Authorization": f"Bearer {owner_token}"}

                stores_response = await client.get(
                    "/api/v1/stores",
                    headers=owner_headers,
                )
                assert stores_response.status_code == 200
                assert stores_response.json()["total"] == 1

                forbidden_response = await client.get(
                    "/api/v1/owners",
                    headers=owner_headers,
                )
                assert forbidden_response.status_code == 403

                forbidden_audit_response = await client.get(
                    "/api/v1/audit-events",
                    headers=owner_headers,
                )
                assert forbidden_audit_response.status_code == 403

                audit_response = await client.get(
                    "/api/v1/audit-events?entity_type=user",
                    headers=manager_headers,
                )
                assert audit_response.status_code == 200
                assert audit_response.json()["total"] == 1
                assert audit_response.json()["items"][0]["action"] == "owner.created"
                assert "password" not in audit_response.text.lower()

                reset_response = await client.post(
                    f"/api/v1/owners/{owner_id}/reset-password",
                    headers=manager_headers,
                    json={"new_password": new_password},
                )
                assert reset_response.status_code == 204

                revoked_response = await client.get(
                    "/api/v1/auth/me",
                    headers=owner_headers,
                )
                assert revoked_response.status_code == 401

                old_login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "organization_slug": organization_slug,
                        "email": owner_email,
                        "password": initial_password,
                    },
                )
                assert old_login_response.status_code == 401

                new_login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "organization_slug": organization_slug,
                        "email": owner_email,
                        "password": new_password,
                    },
                )
                assert new_login_response.status_code == 200

                suspend_response = await client.post(
                    f"/api/v1/owners/{owner_id}/suspend",
                    headers=manager_headers,
                )
                assert suspend_response.status_code == 204

                suspended_login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "organization_slug": organization_slug,
                        "email": owner_email,
                        "password": new_password,
                    },
                )
                assert suspended_login_response.status_code == 401

                activate_response = await client.post(
                    f"/api/v1/owners/{owner_id}/activate",
                    headers=manager_headers,
                )
                assert activate_response.status_code == 204

                unassign_response = await client.delete(
                    f"/api/v1/stores/{store.id}/owners/{owner_id}",
                    headers=manager_headers,
                )
                assert unassign_response.status_code == 204

                updated_owner_response = await client.get(
                    f"/api/v1/owners/{owner_id}",
                    headers=manager_headers,
                )
                assert updated_owner_response.json()["store_ids"] == []
        finally:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                await session.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            await engine.dispose()

    asyncio.run(scenario())