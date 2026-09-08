import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from gestion_boutiques.config import get_settings
from gestion_boutiques.db.session import async_session_factory, engine
from gestion_boutiques.db.tenant import set_tenant_context
from gestion_boutiques.main import app
from gestion_boutiques.models.inventory import InventoryBalance
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.store import Store, StoreOwnership
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.tokens import create_token_pair

pytestmark = pytest.mark.integration


def test_catalog_configuration_and_owner_visibility() -> None:
    async def scenario() -> None:
        organization_id = uuid4()
        manager = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"manager-{uuid4()}@example.com",
            full_name="Catalog Manager",
            password_hash="unused",
            role=UserRole.MANAGER,
        )
        owner = User(
            id=uuid4(),
            organization_id=organization_id,
            email=f"owner-{uuid4()}@example.com",
            full_name="Catalog Owner",
            password_hash="unused",
            role=UserRole.OWNER,
        )
        assigned_store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Assigned Catalog Store",
            code=f"CAT-{str(uuid4())[:8]}",
        )
        hidden_store = Store(
            id=uuid4(),
            organization_id=organization_id,
            name="Hidden Catalog Store",
            code=f"HID-{str(uuid4())[:8]}",
        )
        try:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                session.add(
                    Organization(
                        id=organization_id,
                        name="Catalog API Test",
                        slug=f"catalog-{uuid4()}",
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
                category_response = await client.post(
                    "/api/v1/catalog/categories",
                    headers=manager_headers,
                    json={"name": " Boissons "},
                )
                assert category_response.status_code == 201
                category_id = category_response.json()["id"]

                product_response = await client.post(
                    "/api/v1/catalog/products",
                    headers=manager_headers,
                    json={
                        "category_id": category_id,
                        "name": "Jus de bissap",
                        "sku": " bissap-1l ",
                        "unit": "liter",
                    },
                )
                assert product_response.status_code == 201
                assert product_response.json()["sku"] == "BISSAP-1L"
                product_id = product_response.json()["id"]

                duplicate_response = await client.post(
                    "/api/v1/catalog/products",
                    headers=manager_headers,
                    json={"name": "Doublon", "sku": "BISSAP-1L"},
                )
                assert duplicate_response.status_code == 409

                configure_response = await client.put(
                    f"/api/v1/catalog/stores/{assigned_store.id}/products/{product_id}",
                    headers=manager_headers,
                    json={"unit_price": 1500, "low_stock_threshold": "5.000"},
                )
                assert configure_response.status_code == 200
                assert configure_response.json()["unit_price"] == 1500

                hidden_product_response = await client.post(
                    "/api/v1/catalog/products",
                    headers=manager_headers,
                    json={"name": "Produit caché", "sku": f"HIDDEN-{str(uuid4())[:8]}"},
                )
                assert hidden_product_response.status_code == 201
                hidden_product_id = hidden_product_response.json()["id"]
                hidden_configuration_response = await client.put(
                    f"/api/v1/catalog/stores/{hidden_store.id}/products/{hidden_product_id}",
                    headers=manager_headers,
                    json={"unit_price": 2000, "low_stock_threshold": "2.000"},
                )
                assert hidden_configuration_response.status_code == 200

                owner_products_response = await client.get(
                    "/api/v1/catalog/products",
                    headers=owner_headers,
                )
                assert owner_products_response.status_code == 200
                assert owner_products_response.json()["total"] == 1

                hidden_product_detail_response = await client.get(
                    f"/api/v1/catalog/products/{hidden_product_id}",
                    headers=owner_headers,
                )
                assert hidden_product_detail_response.status_code == 404

                owner_store_products_response = await client.get(
                    f"/api/v1/catalog/stores/{assigned_store.id}/products",
                    headers=owner_headers,
                )
                assert owner_store_products_response.status_code == 200
                assert owner_store_products_response.json()["total"] == 1

                hidden_response = await client.get(
                    f"/api/v1/catalog/stores/{hidden_store.id}/products",
                    headers=owner_headers,
                )
                assert hidden_response.status_code == 404

                forbidden_response = await client.patch(
                    f"/api/v1/catalog/products/{product_id}",
                    headers=owner_headers,
                    json={"name": "Modification interdite"},
                )
                assert forbidden_response.status_code == 403

            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                balance = await session.scalar(
                    select(InventoryBalance).where(
                        InventoryBalance.organization_id == organization_id,
                        InventoryBalance.store_id == assigned_store.id,
                        InventoryBalance.product_id == product_id,
                    )
                )
                assert balance is not None
                assert balance.quantity == 0
        finally:
            async with async_session_factory() as session, session.begin():
                await set_tenant_context(session, organization_id)
                await session.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            await engine.dispose()

    asyncio.run(scenario())