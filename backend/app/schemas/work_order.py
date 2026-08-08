from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.work_order import WorkOrderStatus


def normalize_optional(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    return normalized or None


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qa_record_id: int = Field(gt=0)
    symptom: str = Field(min_length=1, max_length=2000)
    attempted_steps: str | None = Field(default=None, max_length=4000)
    additional_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("symptom", mode="before")
    @classmethod
    def normalize_required(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("故障现象不能为空")
        return normalized

    @field_validator("attempted_steps", "additional_notes", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        return normalize_optional(value)


class WorkOrderQARead(BaseModel):
    id: int
    question: str
    answer: str
    resources: list[dict[str, str]]
    created_at: datetime


class WorkOrderCreatorRead(BaseModel):
    username: str
    display_name: str


class WorkOrderRead(BaseModel):
    id: int
    qa_record: WorkOrderQARead
    creator: WorkOrderCreatorRead | None = None
    symptom: str
    attempted_steps: str | None
    additional_notes: str | None
    solution: str | None
    unresolved_note: str | None
    status: WorkOrderStatus
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def mark_database_time_as_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class WorkOrderPage(BaseModel):
    items: list[WorkOrderRead]
    total: int
    page: int
    page_size: int


class WorkOrderLinksRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qa_record_ids: list[int]

    @field_validator("qa_record_ids")
    @classmethod
    def validate_ids(cls, values: list[int]) -> list[int]:
        unique = list(dict.fromkeys(values))
        if not unique or len(unique) > 50 or any(value <= 0 for value in unique):
            raise ValueError("问答 ID 必须为最多 50 个去重正整数")
        return unique


class WorkOrderLinkRead(BaseModel):
    qa_record_id: int
    work_order_id: int | None


class WorkOrderLinksResponse(BaseModel):
    items: list[WorkOrderLinkRead]


class WorkOrderProcessingContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solution: str | None = Field(default=None, max_length=8000)

    @field_validator("solution", mode="before")
    @classmethod
    def normalize_fields(cls, value: str | None) -> str | None:
        return normalize_optional(value)


class WorkOrderResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solution: str = Field(max_length=8000)

    @field_validator("solution", mode="before")
    @classmethod
    def normalize_solution(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class WorkOrderReopen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unresolved_note: str = Field(max_length=2000)

    @field_validator("unresolved_note", mode="before")
    @classmethod
    def normalize_note(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value
