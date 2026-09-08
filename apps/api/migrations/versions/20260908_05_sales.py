"""Create sales and connect them to inventory movements.

Revision ID: 20260908_05
Revises: 20260908_04
Create Date: 2026-09-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_05"
down_revision: str | None = "20260908_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_SETTING = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def enable_immutable_tenant_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table_name}_select_policy ON {table_name}
        FOR SELECT USING (organization_id = {TENANT_SETTING})
        """
    )
    op.execute(
        f"""
        CREATE POLICY {table_name}_insert_policy ON {table_name}
        FOR INSERT WITH CHECK (organization_id = {TENANT_SETTING})
        """
    )


def upgrade() -> None:
    op.execute("ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS 'sale'")

    op.create_table(
        "sales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("total_amount >= 0", name="ck_sales_total_amount_nonnegative"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_sales_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_sales_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id", "organization_id"],
            ["stores.id", "stores.organization_id"],
            name=op.f("fk_sales_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales")),
        sa.UniqueConstraint("id", "organization_id", name="uq_sales_id_organization"),
    )
    op.create_index("ix_sales_store_created_at", "sales", ["store_id", "created_at"])

    op.create_table(
        "sale_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sale_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.CheckConstraint("line_total >= 0", name="ck_sale_lines_line_total_nonnegative"),
        sa.CheckConstraint("quantity > 0", name="ck_sale_lines_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_lines_unit_price_nonnegative"),
        sa.ForeignKeyConstraint(
            ["sale_id", "organization_id"],
            ["sales.id", "sales.organization_id"],
            name=op.f("fk_sale_lines_sale_id_sales"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            name=op.f("fk_sale_lines_organization_id_store_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_lines")),
        sa.UniqueConstraint("sale_id", "product_id", name="uq_sale_lines_sale_product"),
    )

    op.add_column("stock_movements", sa.Column("sale_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_stock_movements_sale_id_sales",
        "stock_movements",
        "sales",
        ["sale_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_stock_movements_sale_id"), "stock_movements", ["sale_id"])

    enable_immutable_tenant_rls("sales")
    enable_immutable_tenant_rls("sale_lines")


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_movements_sale_id"), table_name="stock_movements")
    op.drop_constraint(
        "fk_stock_movements_sale_id_sales",
        "stock_movements",
        type_="foreignkey",
    )
    op.drop_column("stock_movements", "sale_id")
    op.drop_table("sale_lines")
    op.drop_table("sales")