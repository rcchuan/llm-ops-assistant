from app.models.knowledge_entry import KnowledgeEntryStatus
from app.models.qa_record import QARecord
from app.models.work_order import WorkOrder
from app.services.knowledge_service import build_knowledge_entry


def test_build_knowledge_entry_uses_fixed_markdown_template() -> None:
    order = WorkOrder(
        id=7,
        qa_record_id=3,
        user_id=2,
        symptom="  数据库连接超时  ",
        attempted_steps="  已检查 DNS  ",
        additional_notes="  仅夜间发生  ",
        solution="  调整连接池配置  ",
    )
    record = QARecord(
        id=3,
        user_id=2,
        conversation_id=1,
        question="  MySQL 连接超时怎么处理？  ",
        answer="不得写入候选的 AI 回答",
    )

    entry = build_knowledge_entry(order, record)

    assert entry.work_order_id == 7
    assert entry.title == "MySQL 连接超时怎么处理？"
    assert entry.status == KnowledgeEntryStatus.PENDING
    assert entry.content == (
        "## 故障现象\n数据库连接超时\n\n"
        "## 已尝试步骤\n已检查 DNS\n\n"
        "## 补充说明\n仅夜间发生\n\n"
        "## 解决方案\n调整连接池配置"
    )
    assert "不得写入候选的 AI 回答" not in entry.content


def test_build_knowledge_entry_omits_empty_optional_sections() -> None:
    order = WorkOrder(
        id=8,
        qa_record_id=4,
        user_id=2,
        symptom="磁盘空间不足",
        attempted_steps=None,
        additional_notes="   ",
        solution="清理过期日志",
    )
    record = QARecord(
        id=4,
        user_id=2,
        conversation_id=1,
        question="磁盘满了怎么办？",
        answer="回答",
    )

    entry = build_knowledge_entry(order, record)

    assert entry.content == (
        "## 故障现象\n磁盘空间不足\n\n## 解决方案\n清理过期日志"
    )
    assert "已尝试步骤" not in entry.content
    assert "补充说明" not in entry.content
