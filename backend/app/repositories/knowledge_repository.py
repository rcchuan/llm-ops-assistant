from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import KnowledgeEntryPersistenceError
from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus


class KnowledgeRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_entries(
        self, *, page: int, page_size: int
    ) -> tuple[list[KnowledgeEntry], int]:
        pending_group = case(
            (KnowledgeEntry.status == KnowledgeEntryStatus.SYNCED, 1),
            else_=0,
        )
        try:
            entries = self.session.scalars(
                select(KnowledgeEntry)
                .order_by(
                    pending_group,
                    KnowledgeEntry.created_at.desc(),
                    KnowledgeEntry.id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            total = self.session.scalar(
                select(func.count()).select_from(KnowledgeEntry)
            ) or 0
            return list(entries), total
        except SQLAlchemyError:
            self.session.rollback()
            raise KnowledgeEntryPersistenceError from None

    def get(self, entry_id: int, *, for_update: bool = False) -> KnowledgeEntry | None:
        statement = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        if for_update:
            statement = statement.with_for_update()
        try:
            return self.session.scalar(statement)
        except SQLAlchemyError:
            self.session.rollback()
            raise KnowledgeEntryPersistenceError from None

    def save(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise KnowledgeEntryPersistenceError from None
        return entry
