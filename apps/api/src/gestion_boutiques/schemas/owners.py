from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from gestion_boutiques.models.user import UserRole


class OwnerCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class OwnerUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "OwnerUpdate":
        if not self.model_fields_set:
            raise ValueError("Au moins un champ doit être fourni")
        for field in ("email", "full_name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Le champ {field} ne peut pas être nul")
        return self


class OwnerPasswordReset(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    store_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class OwnerListResponse(BaseModel):
    items: list[OwnerResponse]
    total: int
    page: int
    page_size: int