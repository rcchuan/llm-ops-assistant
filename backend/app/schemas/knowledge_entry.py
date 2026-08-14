from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.knowledge_entry import KnowledgeEntryStatus


class KnowledgeEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_id: int
    title: str
    content: str
    status: KnowledgeEntryStatus
    dify_document_id: str | None
    sync_error: str | None
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("synced_at", "created_at", "updated_at", mode="before")
    @classmethod
    def mark_database_time_as_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class KnowledgeEntryPage(BaseModel):
    items: list[KnowledgeEntryRead]
    total: int
    page: int
    page_size: int


class KnowledgeEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=1000)
    content: str

    @field_validator("title", "content", mode="before")
    @classmethod
    def normalize_required(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("标题和正文不能为空")
        return normalized
