from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SaleLineCreate(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)


class SaleCreate(BaseModel):
    store_id: UUID
    lines: list[SaleLineCreate] = Field(min_length=1, max_length=100)


class SaleLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    quantity: Decimal
    unit_price: int
    line_total: Decimal


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    store_id: UUID
    actor_user_id: UUID | None
    total_amount: Decimal
    created_at: datetime
    lines: list[SaleLineResponse]


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    total: int
    page: int
    page_size: int