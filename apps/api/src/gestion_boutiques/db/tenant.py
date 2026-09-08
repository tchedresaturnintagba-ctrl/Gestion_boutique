from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, organization_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
        {"organization_id": str(organization_id)},
    )


async def set_authentication_context(session: AsyncSession, organization_slug: str) -> None:
    await session.execute(
        text("SELECT set_config('app.authentication_organization_slug', :slug, true)"),
        {"slug": organization_slug},
    )