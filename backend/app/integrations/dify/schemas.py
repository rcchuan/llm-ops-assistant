from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrieverResource:
    document_name: str
    content: str


@dataclass(frozen=True, slots=True)
class DifyChatResult:
    answer: str
    conversation_id: str
    message_id: str | None
    resources: list[RetrieverResource]
