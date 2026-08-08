from app.core.exceptions import (
    KnowledgeEntryConflictError,
    KnowledgeEntryForbiddenError,
    KnowledgeEntryNotFoundError,
)
from app.integrations.dify.dataset_client import DifyDatasetClient
from app.integrations.dify.dataset_exceptions import (
    DifyDatasetConfigurationError,
    DifyDatasetInvalidResponseError,
    DifyDatasetRequestError,
    DifyDatasetUncertainError,
)
from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus, utc_now
from app.models.qa_record import QARecord
from app.models.user import User, UserRole
from app.models.work_order import WorkOrder
from app.repositories.knowledge_repository import KnowledgeRepository


def build_knowledge_entry(order: WorkOrder, record: QARecord) -> KnowledgeEntry:
    sections = [("故障现象", order.symptom.strip())]
    if order.attempted_steps and order.attempted_steps.strip():
        sections.append(("已尝试步骤", order.attempted_steps.strip()))
    if order.additional_notes and order.additional_notes.strip():
        sections.append(("补充说明", order.additional_notes.strip()))
    sections.append(("解决方案", (order.solution or "").strip()))
    return KnowledgeEntry(
        work_order_id=order.id,
        title=record.question.strip(),
        content="\n\n".join(f"## {heading}\n{body}" for heading, body in sections),
        status=KnowledgeEntryStatus.PENDING,
    )


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        dataset_client: DifyDatasetClient | None = None,
    ):
        self.repository = repository
        self.dataset_client = dataset_client

    @staticmethod
    def require_admin(user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise KnowledgeEntryForbiddenError

    def list_entries(
        self, user: User, *, page: int, page_size: int
    ) -> tuple[list[KnowledgeEntry], int]:
        self.require_admin(user)
        return self.repository.list_entries(page=page, page_size=page_size)

    def update(
        self,
        user: User,
        entry_id: int,
        *,
        title: str,
        content: str,
    ) -> KnowledgeEntry:
        self.require_admin(user)
        entry = self.repository.get(entry_id, for_update=True)
        if entry is None:
            raise KnowledgeEntryNotFoundError
        if entry.status == KnowledgeEntryStatus.SYNCED:
            raise KnowledgeEntryConflictError
        entry.title = title
        entry.content = content
        entry.status = KnowledgeEntryStatus.PENDING
        entry.sync_error = None
        return self.repository.save(entry)

    def sync(self, user: User, entry_id: int) -> KnowledgeEntry:
        self.require_admin(user)
        entry = self.repository.get(entry_id, for_update=True)
        if entry is None:
            raise KnowledgeEntryNotFoundError
        if entry.status not in {
            KnowledgeEntryStatus.PENDING,
            KnowledgeEntryStatus.SYNC_FAILED,
        }:
            raise KnowledgeEntryConflictError
        if self.dataset_client is None:
            raise DifyDatasetConfigurationError("知识同步服务未配置")

        try:
            result = self.dataset_client.create_text_document(
                name=f"{entry.title} [KE-{entry.id}]",
                text=entry.content,
            )
        except DifyDatasetConfigurationError:
            self._save_sync_failure(entry, "Dify 配置或认证失败")
            raise
        except DifyDatasetRequestError:
            self._save_sync_failure(entry, "Dify 未接受知识文档")
            raise
        except DifyDatasetUncertainError:
            self._save_sync_failure(entry, self._manual_check_message(entry.id))
            raise
        except DifyDatasetInvalidResponseError:
            self._save_sync_failure(
                entry,
                f"Dify 返回数据无效；{self._manual_check_message(entry.id)}",
            )
            raise

        entry.status = KnowledgeEntryStatus.SYNCED
        entry.dify_document_id = result.document_id
        entry.sync_error = None
        entry.synced_at = utc_now()
        return self.repository.save(entry)

    def _save_sync_failure(self, entry: KnowledgeEntry, message: str) -> None:
        entry.status = KnowledgeEntryStatus.SYNC_FAILED
        entry.dify_document_id = None
        entry.synced_at = None
        entry.sync_error = message[:500]
        self.repository.save(entry)

    @staticmethod
    def _manual_check_message(entry_id: int) -> str:
        return (
            "同步结果不确定，请先在 Dify 控制台按 "
            f"[KE-{entry_id}] 核对后再决定是否重试"
        )
