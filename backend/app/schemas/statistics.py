from pydantic import BaseModel


class QAStatistics(BaseModel):
    total_count: int
    operator_count: int
    converted_count: int
    conversion_rate: float | None


class FeedbackStatistics(BaseModel):
    helpful_count: int
    unhelpful_count: int
    unrated_count: int
    satisfaction_rate: float | None


class StatisticsOverview(BaseModel):
    qa: QAStatistics
    feedback: FeedbackStatistics
    work_orders: dict[str, int]
    knowledge_entries: dict[str, int]
