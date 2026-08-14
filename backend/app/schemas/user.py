from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.user_validation import normalize_display_name, normalize_username
from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    @field_validator("created_at", "updated_at", "last_login_at", mode="before")
    @classmethod
    def mark_database_times_as_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    display_name: str
    initial_password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return normalize_display_name(value)


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool


class PasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(min_length=8, max_length=128)


class UserList(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int
