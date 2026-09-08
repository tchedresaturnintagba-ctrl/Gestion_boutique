import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.store import Store

pytestmark = pytest.mark.integration


def test_application_role_is_limited_and_rls_isolates_stores() -> None:
    async def scenario() -> None:
        organization_a_id = uuid4()
        organization_b_id = uuid4()

        try:
            async with async_session_factory() as session:
                transaction = await session.begin()
                try:
                    role = (
                        await session.execute(
                            text(
                                """
                                SELECT current_user, rolsuper, rolcreatedb, rolcreaterole
                                FROM pg_roles
                                WHERE rolname = current_user
                                """
                            )
                        )
                    ).one()
                    assert role.current_user == "gestion_boutiques"
                    assert not role.rolsuper
                    assert not role.rolcreatedb
                    assert not role.rolcreaterole

                    await set_tenant_context(session, organization_a_id)
                    session.add(
                        Organization(
                            id=organization_a_id,
                            name="Organisation A",
                            slug=f"a-{uuid4()}",
                        )
                    )
                    session.add(
                        Store(
                            organization_id=organization_a_id,
                            name="Boutique A",
                            code="A",
                        )
                    )
                    await session.flush()

                    await set_tenant_context(session, organization_b_id)
                    session.add(
                        Organization(
                            id=organization_b_id,
                            name="Organisation B",
                            slug=f"b-{uuid4()}",
                        )
                    )
                    session.add(
                        Store(
                            organization_id=organization_b_id,
                            name="Boutique B",
                            code="B",
                        )
                    )
                    await session.flush()

                    await set_tenant_context(session, organization_a_id)
                    visible_stores = (await session.scalars(select(Store))).all()

                    assert [store.name for store in visible_stores] == ["Boutique A"]
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(scenario())