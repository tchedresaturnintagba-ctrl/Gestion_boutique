from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from gestion_boutiques.db.base import Base
from gestion_boutiques.models.mixins import TimestampMixin


class ProductUnit(StrEnum):
    PIECE = "piece"
    PACK = "pack"
    KILOGRAM = "kilogram"
    LITER = "liter"


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_categories_organization_name"),
        UniqueConstraint("id", "organization_id", name="uq_categories_id_organization"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id", "organization_id"],
            ["categories.id", "categories.organization_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("organization_id", "sku", name="uq_products_organization_sku"),
        UniqueConstraint("id", "organization_id", name="uq_products_id_organization"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[UUID | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[ProductUnit] = mapped_column(
        Enum(
            ProductUnit,
            name="product_unit",
            values_callable=lambda units: [unit.value for unit in units],
        ),
        nullable=False,
        default=ProductUnit.PIECE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class StoreProduct(TimestampMixin, Base):
    __tablename__ = "store_products"
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"],
            ["stores.id", "stores.organization_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["product_id", "organization_id"],
            ["products.id", "products.organization_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("unit_price >= 0", name="unit_price_nonnegative"),
        CheckConstraint("low_stock_threshold >= 0", name="threshold_nonnegative"),
    )

    organization_id: Mapped[UUID] = mapped_column(primary_key=True)
    store_id: Mapped[UUID] = mapped_column(primary_key=True)
    product_id: Mapped[UUID] = mapped_column(primary_key=True)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    low_stock_threshold: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
        default=Decimal(0),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)