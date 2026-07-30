# -*- coding: utf-8 -*-
"""
模块 3：语料批量治理脚本

功能:
  - 原始杂乱问答：去重、剔除无效符号、问答配对校验
  - 批量格式化 Dify 标准知识库导入 JSON
  - 调用 Dify API 一键上传知识库 (create-by-text)

用法:
    python data_clean.py --clean          # 清洗 raw -> corpus_clean 表 + JSON
    python data_clean.py --upload         # 上传 Markdown 语料到 Dify
    python data_clean.py --all            # 清洗 + 生成 JSON + 上传
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import config
from db_utils import execute, fetch_all
from http_utils import post_json

# 无效符号 / 噪音字符
NOISE_PATTERN = re.compile(r"[!！?？]{2,}|\.{3,}|@{2,}|#+$")
MULTI_SPACE = re.compile(r"\s+")

# 四类运维语料 Markdown 文件（清洗后上传 Dify）
CORPUS_FILES = [
    ("服务器故障", "server_fault.md"),
    ("数据库报错", "database_error.md"),
    ("基站运维", "base_station.md"),
    ("工单流程", "ticket_workflow.md"),
]


def normalize_text(text: str) -> str:
    """去无效符号、合并空白。"""
    t = text.strip()
    t = NOISE_PATTERN.sub("", t)
    t = MULTI_SPACE.sub(" ", t)
    return t


def is_valid_qa_pair(question: str, answer: str) -> bool:
    """问答配对校验：问题和答案均非空且长度合理。"""
    if len(question) < 4 or len(answer) < 4:
        return False
    if question == answer:
        return False
    return True


def load_raw_from_db() -> list[dict]:
    return fetch_all("SELECT id, category, question, answer, source_file FROM corpus_raw")


def load_raw_from_file(path: Path) -> list[dict[str, str]]:
    """
    从 raw 文本文件解析 Q/A 对。
    格式: Q: 问题  /  A: 答案  （空行分隔）
    """
    if not path.exists():
        return []
    items: list[dict[str, str]] = []
    current_q, current_a = "", ""
    category = "未分类"

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            if current_q and current_a:
                items.append({"category": category, "question": current_q, "answer": current_a})
                current_q, current_a = "", ""
            continue
        if line.startswith("#"):
            category = line.lstrip("#").strip()
            continue
        if line.upper().startswith("Q:"):
            current_q = line[2:].strip()
        elif line.upper().startswith("A:"):
            current_a = line[2:].strip()

    if current_q and current_a:
        items.append({"category": category, "question": current_q, "answer": current_a})
    return items


def clean_corpus(save_json: bool = True) -> list[dict[str, Any]]:
    """
    清洗语料：去重 + 去噪 + 校验，写入 corpus_clean 表。
    同时导出 Dify 标准 JSON。
    """
    raw_items = load_raw_from_db()
    file_items = load_raw_from_file(config.RAW_CORPUS_DIR / "raw_qa.txt")
    all_items = raw_items + file_items

    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []

    for item in all_items:
        q = normalize_text(str(item.get("question", "")))
        a = normalize_text(str(item.get("answer", "")))
        cat = normalize_text(str(item.get("category", "未分类")))

        if not is_valid_qa_pair(q, a):
            continue

        sig = f"{cat}|{q.lower()}"
        if sig in seen:
            continue
        seen.add(sig)

        execute(
            """
            INSERT INTO corpus_clean (category, question, answer, dify_doc_name, uploaded)
            VALUES (%s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE answer = VALUES(answer)
            """,
            (cat, q, a, f"{cat}_{len(cleaned)+1}"),
        )
        cleaned.append({"category": cat, "question": q, "answer": a})

    print(f"[清洗] 有效语料 {len(cleaned)} 条")

    if save_json:
        export_dify_json(cleaned)
    return cleaned


def export_dify_json(items: list[dict[str, Any]]) -> Path:
    """
    导出 Dify 知识库标准 JSON 格式。
    结构: { "data": [ { "question": "", "answer": "" }, ... ] }
    适用于 QA 模式导入或备份。
    """
    out_path = config.CORPUS_DIR / "dify_import.json"
    payload = {
        "version": "1.0",
        "description": "移动运维知识库标准导入格式",
        "segments": [
            {
                "question": item["question"],
                "answer": item["answer"],
                "keywords": [item["category"]],
            }
            for item in items
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[导出] JSON 已保存: {out_path}")
    return out_path


def _read_markdown_corpus(filename: str) -> str:
    path = config.CORPUS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"语料文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def upload_markdown_to_dify(dry_run: bool = False) -> int:
    """
    将四类 Markdown 运维语料通过 create-by-text API 上传到 Dify 知识库。
    """
    config.validate_dify_dataset_config()
    url = f"{config.DIFY_BASE_URL}/datasets/{config.DIFY_DATASET_ID}/document/create-by-text"
    headers = {
        "Authorization": f"Bearer {config.DIFY_DATASET_API_KEY}",
        "Content-Type": "application/json",
    }

    uploaded = 0
    for category, filename in CORPUS_FILES:
        text = _read_markdown_corpus(filename)
        doc_name = f"运维语料_{category}"
        payload = {
            "name": doc_name,
            "text": text,
            "indexing_technique": "high_quality",
            "process_rule": {"mode": "automatic"},
        }
        if dry_run:
            print(f"[DRY-RUN] 将上传: {doc_name} ({len(text)} 字符)")
            uploaded += 1
            continue

        resp = post_json(url, headers=headers, payload=payload, timeout=120)
        resp.raise_for_status()
        batch = resp.json().get("batch", "")
        print(f"[上传] {doc_name} batch={batch}")
        uploaded += 1
        time.sleep(2)

    return uploaded


def upload_qa_segments_to_dify(limit: int = 50) -> int:
    """将 corpus_clean 表中未上传的 Q/A 合并为文本文档上传。"""
    config.validate_dify_dataset_config()
    rows = fetch_all(
        "SELECT id, category, question, answer FROM corpus_clean WHERE uploaded = 0 LIMIT %s",
        (limit,),
    )
    if not rows:
        print("[上传] corpus_clean 无待上传记录")
        return 0

    grouped: dict[str, list[str]] = {}
    ids: list[int] = []
    for row in rows:
        block = f"### Q: {row['question']}\nA: {row['answer']}\n"
        grouped.setdefault(row["category"], []).append(block)
        ids.append(row["id"])

    url = f"{config.DIFY_BASE_URL}/datasets/{config.DIFY_DATASET_ID}/document/create-by-text"
    headers = {
        "Authorization": f"Bearer {config.DIFY_DATASET_API_KEY}",
        "Content-Type": "application/json",
    }
    uploaded = 0
    for cat, blocks in grouped.items():
        text = f"## 清洗语料 · {cat}\n\n" + "\n".join(blocks)
        doc_name = f"清洗语料_{cat}_{int(time.time())}"
        payload = {
            "name": doc_name,
            "text": text,
            "indexing_technique": "high_quality",
            "process_rule": {"mode": "automatic"},
        }
        resp = post_json(url, headers=headers, payload=payload, timeout=120)
        resp.raise_for_status()
        uploaded += 1
        print(f"[上传] {doc_name}")

    for row_id in ids:
        execute("UPDATE corpus_clean SET uploaded = 1 WHERE id = %s", (row_id,))

    return uploaded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运维语料治理")
    parser.add_argument("--clean", action="store_true", help="清洗语料")
    parser.add_argument("--upload", action="store_true", help="上传 Markdown 到 Dify")
    parser.add_argument("--upload-qa", action="store_true", help="上传清洗 Q/A 到 Dify")
    parser.add_argument("--dry-run", action="store_true", help="仅预览上传")
    parser.add_argument("--all", action="store_true", help="清洗 + 上传")
    args = parser.parse_args(argv)

    if not any([args.clean, args.upload, args.upload_qa, args.all]):
        parser.print_help()
        return 1

    try:
        if args.all or args.clean:
            clean_corpus(save_json=True)
        if args.all or args.upload:
            upload_markdown_to_dify(dry_run=args.dry_run)
        if args.upload_qa:
            upload_qa_segments_to_dify()
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
