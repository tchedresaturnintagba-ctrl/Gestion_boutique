from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestion_boutiques.db.base import Base
from gestion_boutiques.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from gestion_boutiques.models.organization import Organization
    from gestion_boutiques.models.user import User


class Store(TimestampMixin, Base):
    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_stores_organization_code"),
        UniqueConstraint("id", "organization_id", name="uq_stores_id_organization"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization: Mapped[Organization] = relationship(back_populates="stores")
    ownerships: Mapped[list[StoreOwnership]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )


class StoreOwnership(Base):
    __tablename__ = "store_ownerships"

    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        primary_key=True,
    )
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    store: Mapped[Store] = relationship(back_populates="ownerships")
    owner: Mapped[User] = relationship(back_populates="store_ownerships")