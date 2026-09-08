from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestion_boutiques.db.base import Base
from gestion_boutiques.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from gestion_boutiques.models.organization import Organization
    from gestion_boutiques.models.store import StoreOwnership


class UserRole(StrEnum):
    MANAGER = "manager"
    OWNER = "owner"


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_users_organization_email"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    organization: Mapped[Organization] = relationship(back_populates="users")
    store_ownerships: Mapped[list[StoreOwnership]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )