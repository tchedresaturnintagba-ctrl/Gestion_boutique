from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StoreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    address: str | None = Field(default=None, max_length=255)

    @field_validator("name", "address")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=40,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    address: str | None = Field(default=None, max_length=255)

    @field_validator("name", "address")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "StoreUpdate":
        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être fourni")
        for field in ("name", "code"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Le champ {field} ne peut pas être nul")
        return self


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    code: str
    address: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StoreListResponse(BaseModel):
    items: list[StoreResponse]
    total: int
    page: int
    page_size: int