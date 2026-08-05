from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_latest_by_user(self, user_id: int) -> Conversation | None:
        return self.session.scalar(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .limit(1)
        )

    def get_owned_by_id(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation | None:
        return self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
