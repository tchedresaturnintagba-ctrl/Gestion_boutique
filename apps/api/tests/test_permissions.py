import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from gestion_boutiques.api.dependencies import require_roles
from gestion_boutiques.models.user import User, UserRole


def build_user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        organization_id=uuid4(),
        email=f"{role.value}@example.com",
        full_name=role.value.title(),
        password_hash="unused",
        role=role,
    )


def test_manager_role_is_accepted() -> None:
    manager_only = require_roles(UserRole.MANAGER)
    manager = build_user(UserRole.MANAGER)

    assert asyncio.run(manager_only(manager)) is manager


def test_owner_role_is_rejected_from_manager_permission() -> None:
    manager_only = require_roles(UserRole.MANAGER)

    with pytest.raises(HTTPException) as error:
        asyncio.run(manager_only(build_user(UserRole.OWNER)))

    assert error.value.status_code == 403
    assert error.value.detail == "Permissions insuffisantes"