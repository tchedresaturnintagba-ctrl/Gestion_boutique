from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from gestion_boutiques.db.tenant import set_authentication_context, set_tenant_context
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.user import User
from gestion_boutiques.security.passwords import verify_password


async def authenticate_user(
    session: AsyncSession,
    *,
    organization_slug: str,
    email: str,
    password: str,
) -> User | None:
    await set_authentication_context(session, organization_slug)
    organization = await session.scalar(
        select(Organization).where(
            Organization.slug == organization_slug,
            Organization.is_active.is_(True),
        )
    )
    if organization is None:
        return None

    await set_tenant_context(session, organization.id)
    user = await session.scalar(
        select(User).where(
            User.organization_id == organization.id,
            func.lower(User.email) == email.lower(),
            User.is_active.is_(True),
        )
    )
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user