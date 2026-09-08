import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.main import app
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.passwords import hash_password

pytestmark = pytest.mark.integration


def test_login_and_read_current_user() -> None:
    async def scenario() -> None:
        organization_id = uuid4()
        organization_slug = f"auth-{uuid4()}"
        email = f"manager-{uuid4()}@example.com"
        password = "a-secure-test-password"

        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                session.add(
                    Organization(
                        id=organization_id,
                        name="Authentication Test",
                        slug=organization_slug,
                    )
                )
                session.add(
                    User(
                        organization_id=organization_id,
                        email=email,
                        full_name="Test Manager",
                        password_hash=hash_password(password),
                        role=UserRole.MANAGER,
                    )
                )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "organization_slug": organization_slug,
                        "email": email,
                        "password": password,
                    },
                )
                assert login_response.status_code == 200
                tokens = login_response.json()
                assert tokens["token_type"] == "bearer"
                assert tokens["access_token"] != tokens["refresh_token"]

                profile_response = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                assert profile_response.status_code == 200
                assert profile_response.json() == {
                    "id": profile_response.json()["id"],
                    "organization_id": str(organization_id),
                    "email": email,
                    "full_name": "Test Manager",
                    "role": "manager",
                }

                refresh_response = await client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": tokens["refresh_token"]},
                )
                assert refresh_response.status_code == 200

                logout_response = await client.post(
                    "/api/v1/auth/logout-all",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                assert logout_response.status_code == 204

                rejected_response = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                assert rejected_response.status_code == 401
        finally:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                await session.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            await engine.dispose()

    asyncio.run(scenario())