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
from gestion_boutiques.models.inventory import StockMovement
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.store import Store, StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import create_token_pair

pytestmark = pytest.mark.integration


def test_stock_movements_alerts_and_concurrent_output() -> None:
    async def scenario() -> None:
        organization_id = uuid4()
        manager = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"manager-{uuid4()}@example.com",
            full_name="Inventory Manager",
            password_hash="unused",
            role=UserRole.MANAGER,
        )
        owner = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"owner-{uuid4()}@example.com",
            full_name="Inventory Owner",
            password_hash="unused",
            role=UserRole.OWNER,
        )
        assigned_store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Inventory Store",
            code=f"INV-{str(uuid4())[:8]}",
        )
        hidden_store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Hidden Inventory Store",
            code=f"HINV-{str(uuid4())[:8]}",
        )
        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                session.add(
                    Organization(
                        id=organization_id,
                        name="Inventory API Test",
                        slug=f"inventory-{uuid4()}",
                    )
                )
                session.add_all([manager, owner, assigned_store, hidden_store])
                session.add(StoreOwnership(store_id=assigned_store.id, owner_id=owner.id))

            settings = get_settings()
            manager_headers = {
                "Authorization": f"Bearer {create_token_pair(manager, settings).access_token}"
            }
            owner_headers = {
                "Authorization": f"Bearer {create_token_pair(owner, settings).access_token}"
            }
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                product_response = await client.post(
                    "/api/v1/catalog/products",
                    headers=manager_headers,
                    json={"name": "Riz parfumé", "sku": f"RIZ-{str(uuid4())[:8]}"},
                )
                assert product_response.status_code == 201
                product_id = product_response.json()["id"]

                configuration_response = await client.put(
                    f"/api/v1/catalog/stores/{assigned_store.id}/products/{product_id}",
                    headers=manager_headers,
                    json={"unit_price": 18000, "low_stock_threshold": "5.000"},
                )
                assert configuration_response.status_code == 200
                movement_url = f"/api/v1/inventory/stores/{assigned_store.id}/movements"

                owner_write_response = await client.post(
                    movement_url,
                    headers=owner_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "entry",
                        "quantity": "1.000",
                        "reason": "Interdit",
                    },
                )
                assert owner_write_response.status_code == 403

                entry_response = await client.post(
                    movement_url,
                    headers=manager_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "entry",
                        "quantity": "10.000",
                        "reason": "Stock initial",
                    },
                )
                assert entry_response.status_code == 201
                assert Decimal(entry_response.json()["balance"]["quantity"]) == 10
                assert entry_response.json()["alert"] is None

                low_stock_response = await client.post(
                    movement_url,
                    headers=manager_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "adjustment_out",
                        "quantity": "6.000",
                        "reason": "Comptage physique",
                    },
                )
                assert low_stock_response.status_code == 201
                assert low_stock_response.json()["alert"]["alert_type"] == "low_stock"

                balances_response = await client.get(
                    f"/api/v1/inventory/stores/{assigned_store.id}/balances",
                    headers=owner_headers,
                )
                assert balances_response.status_code == 200
                assert Decimal(balances_response.json()["items"][0]["quantity"]) == 4

                alerts_response = await client.get(
                    f"/api/v1/inventory/alerts?store_id={assigned_store.id}",
                    headers=owner_headers,
                )
                assert alerts_response.status_code == 200
                assert alerts_response.json()["total"] == 1

                hidden_response = await client.get(
                    f"/api/v1/inventory/stores/{hidden_store.id}/balances",
                    headers=owner_headers,
                )
                assert hidden_response.status_code == 404

                rejected_response = await client.post(
                    movement_url,
                    headers=manager_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "adjustment_out",
                        "quantity": "5.000",
                        "reason": "Sortie excessive",
                    },
                )
                assert rejected_response.status_code == 409

                resolved_response = await client.post(
                    movement_url,
                    headers=manager_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "adjustment_in",
                        "quantity": "2.000",
                        "reason": "Correction positive",
                    },
                )
                assert resolved_response.status_code == 201
                assert resolved_response.json()["alert"] is None

                history_response = await client.get(
                    "/api/v1/inventory/alerts?open_only=false",
                    headers=manager_headers,
                )
                assert history_response.status_code == 200
                assert history_response.json()["total"] == 1
                assert history_response.json()["items"][0]["resolved_at"] is not None

                out_of_stock_response = await client.post(
                    movement_url,
                    headers=manager_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "adjustment_out",
                        "quantity": "6.000",
                        "reason": "Écart inventaire",
                    },
                )
                assert out_of_stock_response.status_code == 201
                assert out_of_stock_response.json()["alert"]["alert_type"] == "out_of_stock"

                refill_response = await client.post(
                    movement_url,
                    headers=manager_headers,
                    json={
                        "product_id": product_id,
                        "movement_type": "entry",
                        "quantity": "10.000",
                        "reason": "Réapprovisionnement",
                    },
                )
                assert refill_response.status_code == 201

                async def consume_six() -> int:
                    response = await client.post(
                        movement_url,
                        headers=manager_headers,
                        json={
                            "product_id": product_id,
                            "movement_type": "adjustment_out",
                            "quantity": "6.000",
                            "reason": "Sortie concurrente",
                        },
                    )
                    return response.status_code

                concurrent_statuses = await asyncio.gather(consume_six(), consume_six())
                assert sorted(concurrent_statuses) == [201, 409]

                final_balance_response = await client.get(
                    f"/api/v1/inventory/stores/{assigned_store.id}/balances",
                    headers=owner_headers,
                )
                assert Decimal(final_balance_response.json()["items"][0]["quantity"]) == 4

                movements_response = await client.get(
                    movement_url,
                    headers=owner_headers,
                )
                assert movements_response.status_code == 200
                assert movements_response.json()["total"] == 6
                movement_id = movements_response.json()["items"][0]["id"]

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                result = await session.execute(
                    update(StockMovement)
                    .where(StockMovement.id == movement_id)
                    .values(reason="Altération")
                )
                assert result.rowcount == 0
                movement = await session.scalar(
                    select(StockMovement).where(StockMovement.id == movement_id)
                )
                assert movement is not None
                assert movement.reason == "Sortie concurrente"
        finally:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                await session.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            await engine.dispose()

    asyncio.run(scenario())