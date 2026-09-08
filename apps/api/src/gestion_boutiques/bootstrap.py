import argparse
import asyncio
import getpass
from uuid import uuid4

from sqlalchemy import select

from gestion_boutiques.db.session import async_session_factory
from gestion_boutiques.db.tenant import set_authentication_context, set_tenant_context
from gestion_boutiques.models.organization import Organization
from gestion_boutiques.models.user import User, UserRole
from gestion_boutiques.security.passwords import hash_password


async def bootstrap_manager(args: argparse.Namespace) -> None:
    password = getpass.getpass("Mot de passe du gestionnaire: ")
    confirmation = getpass.getpass("Confirmez le mot de passe: ")
    if password != confirmation:
        raise SystemExit("Les mots de passe ne correspondent pas.")
    if len(password) < 12:
        raise SystemExit("Le mot de passe doit contenir au moins 12 caractères.")

    async with async_session_factory() as session, session.begin():
        await set_authentication_context(session, args.organization_slug)
        organization = await session.scalar(
            select(Organization).where(Organization.slug == args.organization_slug)
        )
        if organization is None:
            organization = Organization(
                id=uuid4(),
                name=args.organization_name,
                slug=args.organization_slug,
            )
            await set_tenant_context(session, organization.id)
            session.add(organization)
            await session.flush()
        else:
            await set_tenant_context(session, organization.id)

        existing_user = await session.scalar(
            select(User).where(
                User.organization_id == organization.id,
                User.email == args.email.lower(),
            )
        )
        if existing_user is not None:
            raise SystemExit("Un utilisateur avec cet email existe déjà dans l'organisation.")

        session.add(
            User(
                organization_id=organization.id,
                email=args.email.lower(),
                full_name=args.full_name,
                password_hash=hash_password(password),
                role=UserRole.MANAGER,
            )
        )

    print(f"Gestionnaire {args.email.lower()} créé pour {args.organization_name}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialise le premier gestionnaire.")
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--organization-slug", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(bootstrap_manager(parse_args()))