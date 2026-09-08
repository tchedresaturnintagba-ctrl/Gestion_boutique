"""Create immutable audit events.

Revision ID: 20260908_02
Revises: 20260907_01
Create Date: 2026-09-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_02"
down_revision: str | None = "20260907_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_SETTING = "NULLIF(current_setting('app.current_organization_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_organization_created_at",
        "audit_events",
        ["organization_id", "created_at"],
    )
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY audit_events_select_policy ON audit_events
        FOR SELECT USING (organization_id = {TENANT_SETTING})
        """
    )
    op.execute(
        f"""
        CREATE POLICY audit_events_insert_policy ON audit_events
        FOR INSERT WITH CHECK (organization_id = {TENANT_SETTING})
        """
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_organization_created_at", table_name="audit_events")
    op.drop_table("audit_events")