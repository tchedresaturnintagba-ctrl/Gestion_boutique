import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.models.catalog import Category, Product, StoreProduct
from gestion_boutiques.models.inventory import (
    InventoryBalance,
    StockAlert,
    StockAlertType,
    StockMovement,
    StockMovementType,
)
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.store import Store
from gestion_boutiques.models.user import User, UserRole

pytestmark = pytest.mark.integration


def test_catalog_and_inventory_rows_are_isolated_by_tenant() -> None:
    async def scenario() -> None:
        organization_a_id = uuid4()
        organization_b_id = uuid4()
        manager_id = uuid4()
        store_id = uuid4()
        category_id = uuid4()
        product_id = uuid4()
        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_a_id)
                session.add(
                    Organization(
                        id=organization_a_id,
                        name="Sprint 3 Tenant A",
                        slug=f"sprint3-a-{uuid4()}",
                    )
                )
                await session.flush()
                session.add(
                    User(
                        id=manager_id,
                        organization_id=organization_a_id,
                        email=f"manager-{uuid4()}@example.com",
                        full_name="Sprint 3 Manager",
                        password_hash="unused",
                        role=UserRole.MANAGER,
                    )
                )
                session.add(
                    Store(
                        id=store_id,
                        organization_id=organization_a_id,
                        name="Sprint 3 Store",
                        code=f"S3-{str(uuid4())[:8]}",
                    )
                )
                session.add(
                    Category(
                        id=category_id,
                        organization_id=organization_a_id,
                        name="Tenant A Category",
                    )
                )
                await session.flush()
                session.add(
                    Product(
                        id=product_id,
                        organization_id=organization_a_id,
                        category_id=category_id,
                        name="Tenant A Product",
                        sku=f"TENANT-A-{str(uuid4())[:8]}",
                    )
                )
                await session.flush()
                session.add(
                    StoreProduct(
                        organization_id=organization_a_id,
                        store_id=store_id,
                        product_id=product_id,
                        unit_price=1000,
                        low_stock_threshold=Decimal("5.000"),
                    )
                )
                await session.flush()
                session.add(
                    InventoryBalance(
                        organization_id=organization_a_id,
                        store_id=store_id,
                        product_id=product_id,
                        quantity=Decimal("2.000"),
                    )
                )
                session.add(
                    StockMovement(
                        organization_id=organization_a_id,
                        store_id=store_id,
                        product_id=product_id,
                        actor_user_id=manager_id,
                        movement_type=StockMovementType.ENTRY,
                        quantity=Decimal("2.000"),
                        previous_quantity=Decimal(0),
                        new_quantity=Decimal("2.000"),
                        reason="Initialisation RLS",
                    )
                )
                session.add(
                    StockAlert(
                        organization_id=organization_a_id,
                        store_id=store_id,
                        product_id=product_id,
                        alert_type=StockAlertType.LOW_STOCK,
                        observed_quantity=Decimal("2.000"),
                        threshold=Decimal("5.000"),
                    )
                )

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_b_id)
                session.add(
                    Organization(
                        id=organization_b_id,
                        name="Sprint 3 Tenant B",
                        slug=f"sprint3-b-{uuid4()}",
                    )
                )

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_b_id)
                for model in (
                    Category,
                    Product,
                    StoreProduct,
                    InventoryBalance,
                    StockMovement,
                    StockAlert,
                ):
                    count = await session.scalar(select(func.count()).select_from(model))
                    assert count == 0
        finally:
            for organization_id in (organization_a_id, organization_b_id):
                async with async_session_factory() as session, session.begin():
                    await set_tenant_context(session, organization_id)
                    await session.execute(
                        delete(Organization).where(Organization.id == organization_id)
                    )
            await engine.dispose()

    asyncio.run(scenario())