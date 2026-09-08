"""Create identity tables and tenant RLS policies.

Revision ID: 20260907_01
Revises:
Create Date: 2026-09-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_SETTING = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def upgrade() -> None:
    user_role = postgresql.ENUM("manager", "owner", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organizations_slug")),
    )
    op.create_table(
        "stores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_stores_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stores")),
        sa.UniqueConstraint("organization_id", "code", name="uq_stores_organization_code"),
    )
    op.create_index(op.f("ix_stores_organization_id"), "stores", ["organization_id"])
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_organization_email"),
    )
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"])
    op.create_table(
        "store_ownerships",
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_store_ownerships_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_store_ownerships_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("store_id", "owner_id", name=op.f("pk_store_ownerships")),
    )

    for table_name in ("organizations", "users", "stores", "store_ownerships"):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    op.execute(
        f"""
        CREATE POLICY organizations_tenant_policy ON organizations
        USING (
            id = {TENANT_SETTING}
            OR slug = current_setting('app.authentication_organization_slug', true)
        )
        WITH CHECK (id = {TENANT_SETTING})
        """
    )
    for table_name in ("users", "stores"):
        op.execute(
            f"""
            CREATE POLICY {table_name}_tenant_policy ON {table_name}
            USING (organization_id = {TENANT_SETTING})
            WITH CHECK (organization_id = {TENANT_SETTING})
            """
        )
    op.execute(
        f"""
        CREATE POLICY store_ownerships_tenant_policy ON store_ownerships
        USING (
            EXISTS (
                SELECT 1 FROM stores
                WHERE stores.id = store_ownerships.store_id
                  AND stores.organization_id = {TENANT_SETTING}
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM stores
                WHERE stores.id = store_ownerships.store_id
                  AND stores.organization_id = {TENANT_SETTING}
            )
        )
        """
    )


def downgrade() -> None:
    op.drop_table("store_ownerships")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_stores_organization_id"), table_name="stores")
    op.drop_table("stores")
    op.drop_table("organizations")
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)