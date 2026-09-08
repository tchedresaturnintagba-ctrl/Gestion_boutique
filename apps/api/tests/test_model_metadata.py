from gestion_boutiques.db.base import Base
from gestion_boutiques.models import Organization, Store, StoreOwnership, User


def test_identity_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "audit_events",
        "categories",
        "inventory_balances",
        "organizations",
        "products",
        "sale_lines",
        "sales",
        "stock_alerts",
        "stock_movements",
        "store_ownerships",
        "store_products",
        "stores",
        "users",
    }


def test_tenant_models_reference_organization() -> None:
    user_foreign_keys = {key.target_fullname for key in User.__table__.foreign_keys}
    store_foreign_keys = {key.target_fullname for key in Store.__table__.foreign_keys}

    assert user_foreign_keys == {"organizations.id"}
    assert store_foreign_keys == {"organizations.id"}


def test_store_ownership_has_composite_primary_key() -> None:
    primary_key_names = {column.name for column in StoreOwnership.__table__.primary_key}

    assert primary_key_names == {"store_id", "owner_id"}
    assert Organization.__tablename__ == "organizations"