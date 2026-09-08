from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestion_boutiques.db.base import Base


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        ForeignKeyConstraint(
            ["store_id", "organization_id"],
            ["stores.id", "stores.organization_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("total_amount >= 0", name="total_amount_nonnegative"),
        UniqueConstraint("id", "organization_id", name="uq_sales_id_organization"),
        Index("ix_sales_store_created_at", "store_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_id: Mapped[UUID] = mapped_column(nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    lines: Mapped[list[SaleLine]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="SaleLine.id",
    )


class SaleLine(Base):
    __tablename__ = "sale_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["sale_id", "organization_id"],
            ["sales.id", "sales.organization_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_nonnegative"),
        CheckConstraint("line_total >= 0", name="line_total_nonnegative"),
        UniqueConstraint("sale_id", "product_id", name="uq_sale_lines_sale_product"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(nullable=False)
    product_id: Mapped[UUID] = mapped_column(nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="lines")