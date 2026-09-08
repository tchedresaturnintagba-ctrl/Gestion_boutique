from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestion_boutiques.db.base import Base
from gestion_boutiques.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from gestion_boutiques.models.store import Store
    from gestion_boutiques.models.user import User


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    users: Mapped[list[User]] = relationship(back_populates="organization")
    stores: Mapped[list[Store]] = relationship(back_populates="organization")