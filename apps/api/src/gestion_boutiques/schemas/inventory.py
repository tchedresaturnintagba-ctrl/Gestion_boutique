from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gestion_boutiques.models.inventory import StockAlertType, StockMovementType


class StockMovementCreate(BaseModel):
    product_id: UUID
    movement_type: Literal[
        StockMovementType.ENTRY,
        StockMovementType.ADJUSTMENT_IN,
        StockMovementType.ADJUSTMENT_OUT,
    ]
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    reason: str = Field(min_length=2, max_length=255)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class InventoryBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    store_id: UUID
    product_id: UUID
    quantity: Decimal
    updated_at: datetime


class InventoryBalanceListResponse(BaseModel):
    items: list[InventoryBalanceResponse]
    total: int
    page: int
    page_size: int


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    store_id: UUID
    product_id: UUID
    actor_user_id: UUID | None
    sale_id: UUID | None
    movement_type: StockMovementType
    quantity: Decimal
    previous_quantity: Decimal
    new_quantity: Decimal
    reason: str
    created_at: datetime


class StockMovementListResponse(BaseModel):
    items: list[StockMovementResponse]
    total: int
    page: int
    page_size: int


class StockAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    store_id: UUID
    product_id: UUID
    alert_type: StockAlertType
    observed_quantity: Decimal
    threshold: Decimal
    created_at: datetime
    resolved_at: datetime | None


class StockAlertListResponse(BaseModel):
    items: list[StockAlertResponse]
    total: int
    page: int
    page_size: int


class StockMovementResultResponse(BaseModel):
    movement: StockMovementResponse
    balance: InventoryBalanceResponse
    alert: StockAlertResponse | None