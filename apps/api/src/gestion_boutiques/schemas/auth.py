from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from gestion_boutiques.models.user import UserRole


class LoginRequest(BaseModel):
    organization_slug: str = Field(
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole