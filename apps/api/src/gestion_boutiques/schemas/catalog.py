from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gestion_boutiques.models.catalog import ProductUnit


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def reject_empty_or_null(self) -> "CategoryUpdate":
        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être fourni")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Les champs fournis ne peuvent pas être nuls")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int


class ProductCreate(BaseModel):
    category_id: UUID | None = None
    name: str = Field(min_length=2, max_length=160)
    sku: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    description: str | None = Field(default=None, max_length=2000)
    unit: ProductUnit = ProductUnit.PIECE

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9_.-]+$",
    )
    description: str | None = Field(default=None, max_length=2000)
    unit: ProductUnit | None = None
    is_active: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @model_validator(mode="after")
    def reject_empty_or_null_required_fields(self) -> "ProductUpdate":
        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être fourni")
        for field in ("name", "sku", "unit", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Le champ {field} ne peut pas être nul")
        return self


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    category_id: UUID | None
    name: str
    sku: str
    description: str | None
    unit: ProductUnit
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


class StoreProductConfigure(BaseModel):
    unit_price: int = Field(ge=0)
    low_stock_threshold: Decimal = Field(
        default=Decimal(0),
        ge=0,
        max_digits=14,
        decimal_places=3,
    )
    is_active: bool = True


class StoreProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    store_id: UUID
    product_id: UUID
    unit_price: int
    low_stock_threshold: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StoreProductListResponse(BaseModel):
    items: list[StoreProductResponse]
    total: int
    page: int
    page_size: int