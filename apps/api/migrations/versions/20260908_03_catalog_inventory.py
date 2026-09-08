"""Create catalog, inventory, movements and alerts.

Revision ID: 20260908_03
Revises: 20260908_02
Create Date: 2026-09-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_03"
down_revision: str | None = "20260908_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_SETTING = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def enable_tenant_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table_name}_tenant_policy ON {table_name}
        USING (organization_id = {TENANT_SETTING})
        WITH CHECK (organization_id = {TENANT_SETTING})
        """
    )


def upgrade() -> None:
    product_unit = postgresql.ENUM(
        "piece", "pack", "kilogram", "liter", name="product_unit", create_type=False
    )
    movement_type = postgresql.ENUM(
        "entry",
        "adjustment_in",
        "adjustment_out",
        name="stock_movement_type",
        create_type=False,
    )
    alert_type = postgresql.ENUM(
        "out_of_stock", "low_stock", name="stock_alert_type", create_type=False
    )
    product_unit.create(op.get_bind(), checkfirst=True)
    movement_type.create(op.get_bind(), checkfirst=True)
    alert_type.create(op.get_bind(), checkfirst=True)

    op.create_unique_constraint("uq_stores_id_organization", "stores", ["id", "organization_id"])
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_categories_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_categories_organization_name"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_categories_id_organization"),
    )
    op.create_index(op.f("ix_categories_organization_id"), "categories", ["organization_id"])
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", product_unit, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["category_id", "organization_id"],
            ["categories.id", "categories.organization_id"],
            name=op.f("fk_products_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_products_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("organization_id", "sku", name="uq_products_organization_sku"),
        sa.UniqueConstraint("id", "organization_id", name="uq_products_id_organization"),
    )
    op.create_index(op.f("ix_products_organization_id"), "products", ["organization_id"])
    op.create_table(
        "store_products",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("low_stock_threshold", sa.Numeric(14, 3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_store_products_threshold_nonnegative",
        ),
        sa.CheckConstraint("unit_price >= 0", name="ck_store_products_unit_price_nonnegative"),
        sa.ForeignKeyConstraint(
            ["product_id", "organization_id"],
            ["products.id", "products.organization_id"],
            name=op.f("fk_store_products_product_id_products"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id", "organization_id"],
            ["stores.id", "stores.organization_id"],
            name=op.f("fk_store_products_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "organization_id", "store_id", "product_id", name=op.f("pk_store_products")
        ),
    )
    op.create_table(
        "inventory_balances",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_inventory_balances_quantity_nonnegative"),
        sa.ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            name=op.f("fk_inventory_balances_organization_id_store_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "organization_id",
            "store_id",
            "product_id",
            name=op.f("pk_inventory_balances"),
        ),
    )
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("movement_type", movement_type, nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("previous_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("new_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("new_quantity >= 0", name="ck_stock_movements_new_quantity_nonnegative"),
        sa.CheckConstraint(
            "previous_quantity >= 0",
            name="ck_stock_movements_previous_quantity_nonnegative",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_stock_movements_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            name=op.f("fk_stock_movements_organization_id_store_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_movements")),
    )
    op.create_index(
        "ix_stock_movements_store_created_at", "stock_movements", ["store_id", "created_at"]
    )
    op.create_table(
        "stock_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", alert_type, nullable=False),
        sa.Column("observed_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("threshold", sa.Numeric(14, 3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "observed_quantity >= 0",
            name="ck_stock_alerts_observed_quantity_nonnegative",
        ),
        sa.CheckConstraint("threshold >= 0", name="ck_stock_alerts_threshold_nonnegative"),
        sa.ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            name=op.f("fk_stock_alerts_organization_id_store_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_alerts")),
    )
    op.create_index(
        "ix_stock_alerts_organization_created_at",
        "stock_alerts",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "uq_stock_alerts_open_product",
        "stock_alerts",
        ["organization_id", "store_id", "product_id"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )

    for table_name in (
        "categories",
        "products",
        "store_products",
        "inventory_balances",
        "stock_alerts",
    ):
        enable_tenant_rls(table_name)

    op.execute("ALTER TABLE stock_movements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE stock_movements FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY stock_movements_select_policy ON stock_movements
        FOR SELECT USING (organization_id = {TENANT_SETTING})
        """
    )
    op.execute(
        f"""
        CREATE POLICY stock_movements_insert_policy ON stock_movements
        FOR INSERT WITH CHECK (organization_id = {TENANT_SETTING})
        """
    )


def downgrade() -> None:
    op.drop_table("stock_alerts")
    op.drop_table("stock_movements")
    op.drop_table("inventory_balances")
    op.drop_table("store_products")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_constraint("uq_stores_id_organization", "stores", type_="unique")
    postgresql.ENUM(name="stock_alert_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="stock_movement_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="product_unit").drop(op.get_bind(), checkfirst=True)