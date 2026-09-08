from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from gestion_boutiques.db.base import Base


class StockMovementType(StrEnum):
    ENTRY = "entry"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"


class StockAlertType(StrEnum):
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"


class InventoryBalance(Base):
    __tablename__ = "inventory_balances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            ondelete="CASCADE",
        ),
        CheckConstraint("quantity >= 0", name="quantity_nonnegative"),
    )

    organization_id: Mapped[UUID] = mapped_column(primary_key=True)
    store_id: Mapped[UUID] = mapped_column(primary_key=True)
    product_id: Mapped[UUID] = mapped_column(primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
        default=Decimal(0),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
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
        CheckConstraint("previous_quantity >= 0", name="previous_quantity_nonnegative"),
        CheckConstraint("new_quantity >= 0", name="new_quantity_nonnegative"),
        Index("ix_stock_movements_store_created_at", "store_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_id: Mapped[UUID] = mapped_column(nullable=False)
    product_id: Mapped[UUID] = mapped_column(nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(
            StockMovementType,
            name="stock_movement_type",
            values_callable=lambda types: [movement_type.value for movement_type in types],
        ),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    previous_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    new_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class StockAlert(Base):
    __tablename__ = "stock_alerts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "store_id", "product_id"],
            [
                "store_products.organization_id",
                "store_products.store_id",
                "store_products.product_id",
            ],
            ondelete="CASCADE",
        ),
        CheckConstraint("observed_quantity >= 0", name="observed_quantity_nonnegative"),
        CheckConstraint("threshold >= 0", name="threshold_nonnegative"),
        Index(
            "uq_stock_alerts_open_product",
            "organization_id",
            "store_id",
            "product_id",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index("ix_stock_alerts_organization_created_at", "organization_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(nullable=False)
    product_id: Mapped[UUID] = mapped_column(nullable=False)
    alert_type: Mapped[StockAlertType] = mapped_column(
        Enum(
            StockAlertType,
            name="stock_alert_type",
            values_callable=lambda types: [alert_type.value for alert_type in types],
        ),
        nullable=False,
    )
    observed_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))