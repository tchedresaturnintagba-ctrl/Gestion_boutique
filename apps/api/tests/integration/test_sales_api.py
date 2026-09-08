import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from gestion_boutiques.config import get_settings
from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.main import app
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.sale import Sale
from gestion_boutiques.models.store import Store, StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import create_token_pair

pytestmark = pytest.mark.integration


def test_sale_is_atomic_and_updates_inventory() -> None:
    async def scenario() -> None:
        organization_id = uuid4()
        manager = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"sales-manager-{uuid4()}@example.com",
            full_name="Sales Manager",
            password_hash="unused",
            role=UserRole.MANAGER,
        )
        owner = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"sales-owner-{uuid4()}@example.com",
            full_name="Sales Owner",
            password_hash="unused",
            role=UserRole.OWNER,
        )
        store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Sales Store",
            code=f"SALE-{str(uuid4())[:8]}",
        )
        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                session.add(
                    Organization(
                        id=organization_id,
                        name="Sales API Test",
                        slug=f"sales-{uuid4()}",
                    )
                )
                session.add_all([manager, owner, store])
                session.add(StoreOwnership(store_id=store.id, owner_id=owner.id))

            settings = get_settings()
            manager_headers = {
                "Authorization": f"Bearer {create_token_pair(manager, settings).access_token}"
            }
            owner_headers = {
                "Authorization": f"Bearer {create_token_pair(owner, settings).access_token}"
            }
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                product_ids = []
                for name, price, initial_stock in (
                    ("Farine", 1000, "5.000"),
                    ("Huile", 500, "1.000"),
                ):
                    product_response = await client.post(
                        "/api/v1/catalog/products",
                        headers=manager_headers,
                        json={"name": name, "sku": f"{name.upper()}-{str(uuid4())[:8]}"},
                    )
                    assert product_response.status_code == 201
                    product_id = product_response.json()["id"]
                    product_ids.append(product_id)
                    configuration_response = await client.put(
                        f"/api/v1/catalog/stores/{store.id}/products/{product_id}",
                        headers=manager_headers,
                        json={"unit_price": price, "low_stock_threshold": "1.000"},
                    )
                    assert configuration_response.status_code == 200
                    entry_response = await client.post(
                        f"/api/v1/inventory/stores/{store.id}/movements",
                        headers=manager_headers,
                        json={
                            "product_id": product_id,
                            "movement_type": "entry",
                            "quantity": initial_stock,
                            "reason": "Stock initial",
                        },
                    )
                    assert entry_response.status_code == 201

                sale_url = "/api/v1/sales"
                owner_write_response = await client.post(
                    sale_url,
                    headers=owner_headers,
                    json={
                        "store_id": str(store.id),
                        "lines": [{"product_id": product_ids[0], "quantity": "1.000"}],
                    },
                )
                assert owner_write_response.status_code == 403

                rejected_response = await client.post(
                    sale_url,
                    headers=manager_headers,
                    json={
                        "store_id": str(store.id),
                        "lines": [
                            {"product_id": product_ids[0], "quantity": "1.000"},
                            {"product_id": product_ids[1], "quantity": "2.000"},
                        ],
                    },
                )
                assert rejected_response.status_code == 409
                assert rejected_response.json()["detail"]["shortages"][0]["product_id"] == (
                    product_ids[1]
                )

                balances_response = await client.get(
                    f"/api/v1/inventory/stores/{store.id}/balances",
                    headers=manager_headers,
                )
                quantities = {
                    item["product_id"]: Decimal(item["quantity"])
                    for item in balances_response.json()["items"]
                }
                assert quantities == {product_ids[0]: Decimal(5), product_ids[1]: Decimal(1)}

                sale_response = await client.post(
                    sale_url,
                    headers=manager_headers,
                    json={
                        "store_id": str(store.id),
                        "lines": [
                            {"product_id": product_ids[0], "quantity": "1.500"},
                            {"product_id": product_ids[0], "quantity": "0.500"},
                            {"product_id": product_ids[1], "quantity": "1.000"},
                        ],
                    },
                )
                assert sale_response.status_code == 201
                sale = sale_response.json()
                assert Decimal(sale["total_amount"]) == 2500
                assert len(sale["lines"]) == 2
                sale_id = sale["id"]

                balances_response = await client.get(
                    f"/api/v1/inventory/stores/{store.id}/balances",
                    headers=owner_headers,
                )
                quantities = {
                    item["product_id"]: Decimal(item["quantity"])
                    for item in balances_response.json()["items"]
                }
                assert quantities == {product_ids[0]: Decimal(3), product_ids[1]: Decimal(0)}

                movements_response = await client.get(
                    f"/api/v1/inventory/stores/{store.id}/movements?movement_type=sale",
                    headers=owner_headers,
                )
                assert movements_response.status_code == 200
                assert movements_response.json()["total"] == 2
                assert {item["sale_id"] for item in movements_response.json()["items"]} == {
                    sale_id
                }

                alerts_response = await client.get(
                    f"/api/v1/inventory/alerts?store_id={store.id}",
                    headers=owner_headers,
                )
                assert alerts_response.status_code == 200
                assert alerts_response.json()["items"][0]["alert_type"] == "out_of_stock"

                list_response = await client.get(
                    f"{sale_url}?store_id={store.id}",
                    headers=owner_headers,
                )
                assert list_response.status_code == 200
                assert list_response.json()["total"] == 1
                assert list_response.json()["items"][0]["id"] == sale_id

                detail_response = await client.get(
                    f"{sale_url}/{sale_id}",
                    headers=owner_headers,
                )
                assert detail_response.status_code == 200
                assert detail_response.json()["id"] == sale_id

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                result = await session.execute(
                    update(Sale).where(Sale.id == sale_id).values(total_amount=0)
                )
                assert result.rowcount == 0
                stored_sale = await session.scalar(select(Sale).where(Sale.id == sale_id))
                assert stored_sale is not None
                assert stored_sale.total_amount == 2500
        finally:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                await session.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            await engine.dispose()

    asyncio.run(scenario())