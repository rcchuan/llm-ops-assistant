from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.qa_record import FeedbackValue


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)
    start_new: bool = False

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("问题不能为空")
        return normalized


class RetrieverResourceRead(BaseModel):
    document_name: str
    content: str


class ChatMessageRead(BaseModel):
    id: int | None
    question: str
    answer: str
    resources: list[RetrieverResourceRead]
    feedback: FeedbackValue | None
    created_at: datetime
    persisted: bool | None
    conversation_locked: bool

    @field_validator("created_at", mode="before")
    @classmethod
    def mark_database_time_as_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class CurrentChatResponse(BaseModel):
    conversation_id: int | None
    messages: list[ChatMessageRead]


class ChatHistoryResponse(BaseModel):
    items: list[ChatMessageRead]


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback: FeedbackValue
