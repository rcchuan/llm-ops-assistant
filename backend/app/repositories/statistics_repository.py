from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus
from app.models.qa_record import FeedbackValue, QARecord
from app.models.user import User, UserRole
from app.models.work_order import WorkOrder, WorkOrderStatus


class StatisticsRepository:
    def __init__(self, session: Session):
        self.session = session

    def overview(self) -> dict[str, object]:
        total = self.session.scalar(select(func.count(QARecord.id))) or 0
        operator = self.session.scalar(
            select(func.count(QARecord.id)).join(User, User.id == QARecord.user_id).where(User.role == UserRole.OPERATOR)
        ) or 0
        converted = self.session.scalar(
            select(func.count(WorkOrder.id))
            .join(QARecord, QARecord.id == WorkOrder.qa_record_id)
            .join(User, User.id == QARecord.user_id)
            .where(User.role == UserRole.OPERATOR)
        ) or 0
        feedback_rows = self.session.execute(
            select(QARecord.feedback, func.count(QARecord.id)).group_by(QARecord.feedback)
        ).all()
        feedback = {value: 0 for value in (None, FeedbackValue.HELPFUL, FeedbackValue.UNHELPFUL)}
        feedback.update({row[0]: row[1] for row in feedback_rows})
        order_rows = self.session.execute(select(WorkOrder.status, func.count(WorkOrder.id)).group_by(WorkOrder.status)).all()
        knowledge_rows = self.session.execute(select(KnowledgeEntry.status, func.count(KnowledgeEntry.id)).group_by(KnowledgeEntry.status)).all()
        return {
            "total_count": total,
            "operator_count": operator,
            "converted_count": converted,
            "helpful_count": feedback[FeedbackValue.HELPFUL],
            "unhelpful_count": feedback[FeedbackValue.UNHELPFUL],
            "unrated_count": feedback[None],
            "work_orders": {status.value: 0 for status in WorkOrderStatus} | {row[0].value: row[1] for row in order_rows},
            "knowledge_entries": {status.value: 0 for status in KnowledgeEntryStatus} | {row[0].value: row[1] for row in knowledge_rows},
        }
