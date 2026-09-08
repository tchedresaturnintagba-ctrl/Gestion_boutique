"""Allow stock movement cleanup with tenant deletion.

Revision ID: 20260908_04
Revises: 20260908_03
Create Date: 2026-09-08
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260908_04"
down_revision: str | None = "20260908_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_stock_movements_organization_id_organizations",
        "stock_movements",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_stock_movements_organization_id_organizations",
        "stock_movements",
        type_="foreignkey",
    )