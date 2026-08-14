# -*- coding: utf-8 -*-
"""
模块 2：运维工单数据采集 & 预处理

功能:
  - 从 MySQL 批量读取工单
  - 正则/关键词提取故障分类（数据库 / 服务器 / 网络）
  - 筛选重复工单，汇总高频问题
  - 将高频问题推送至 Dify 知识库（create-by-text API）

用法:
    python work_order_sql.py --classify
    python work_order_sql.py --dedup
    python work_order_sql.py --summary
    python work_order_sql.py --push-dify
    python work_order_sql.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from collections import Counter
from typing import Any

import config
from db_utils import execute, fetch_all
from http_utils import post_json, fetch_one

# ---------- 故障分类规则（移动运维场景） ----------
CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "数据库",
        re.compile(
            r"MySQL|Oracle|主从|从库|表空间|慢SQL|Seconds_Behind|数据库|binlog|redo|DBA",
            re.I,
        ),
    ),
    (
        "服务器",
        re.compile(
            r"CPU|内存|磁盘|主机|服务器|OOM|swap|日志盘|/var/log|进程|top\s",
            re.I,
        ),
    ),
    (
        "网络",
        re.compile(
            r"网络|超时|5xx|网关|丢包|Traceroute|登录页面|传输|光路|基站|RRU|LTE|退服",
            re.I,
        ),
    ),
]


def classify_description(text: str) -> str:
    """根据问题描述正则匹配，返回 数据库/服务器/网络/其他。"""
    for category, pattern in CATEGORY_RULES:
        if pattern.search(text):
            return category
    return "其他"


def update_fault_categories() -> int:
    """批量更新工单的 fault_category 字段。"""
    rows = fetch_all("SELECT id, description FROM work_orders")
    updated = 0
    for row in rows:
        cat = classify_description(row["description"])
        execute(
            "UPDATE work_orders SET fault_category = %s WHERE id = %s",
            (cat, row["id"]),
        )
        updated += 1
    print(f"[分类] 已更新 {updated} 条工单 fault_category")
    return updated


def _normalize_for_dedup(text: str) -> str:
    """归一化描述用于重复检测。"""
    t = re.sub(r"\s+", "", text.lower())
    t = re.sub(r"[，。！？、；：""''（）\[\]]", "", t)
    return t[:120]


def mark_duplicate_orders() -> int:
    """标记重复工单：相同归一化描述视为重复。"""
    rows = fetch_all("SELECT id, description FROM work_orders ORDER BY submit_time ASC")
    seen: dict[str, int] = {}
    dup_count = 0
    for row in rows:
        sig = _normalize_for_dedup(row["description"])
        if sig in seen:
            execute(
                "UPDATE work_orders SET is_duplicate = 1 WHERE id = %s",
                (row["id"],),
            )
            dup_count += 1
        else:
            seen[sig] = row["id"]
            execute(
                "UPDATE work_orders SET is_duplicate = 0 WHERE id = %s",
                (row["id"],),
            )
    print(f"[去重] 标记重复工单 {dup_count} 条")
    return dup_count


def summarize_high_freq_issues(min_count: int = 2) -> list[dict[str, Any]]:
    """
    汇总非重复工单中的高频问题（按分类+关键词签名）。
    写入 high_freq_issues 表。
    """
    rows = fetch_all(
        "SELECT id, fault_category, description FROM work_orders WHERE is_duplicate = 0"
    )
    counter: Counter[str] = Counter()
    samples: dict[str, dict] = {}

    for row in rows:
        cat = row["fault_category"]
        # 取描述前 40 字作为特征
        key_text = re.sub(r"\s+", "", row["description"])[:40]
        sig = hashlib.md5(f"{cat}:{key_text}".encode()).hexdigest()
        counter[sig] += 1
        samples[sig] = {
            "category": cat,
            "sample_desc": row["description"],
            "keyword_sig": sig,
        }

    saved = 0
    result = []
    for sig, count in counter.items():
        if count < min_count:
            continue
        info = samples[sig]
        execute(
            """
            INSERT INTO high_freq_issues (category, keyword_sig, sample_desc, hit_count)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE hit_count = VALUES(hit_count), sample_desc = VALUES(sample_desc)
            """,
            (info["category"], sig, info["sample_desc"], count),
        )
        saved += 1
        result.append({**info, "hit_count": count})

    print(f"[汇总] 高频问题 {saved} 条（出现次数>={min_count}）")
    return result


def _build_dify_doc_text(category: str, sample_desc: str, hit_count: int) -> str:
    """将高频工单转为 Dify 知识库文档文本。"""
    return (
        f"## 高频运维问题 · {category}\n\n"
        f"**出现次数**: {hit_count}\n\n"
        f"**典型现象**:\n{sample_desc}\n\n"
        f"**处理建议**:\n"
        f"1. 按 {category} 类标准排查手册逐步定位\n"
        f"2. 采集告警时间、影响范围、相关日志\n"
        f"3. 若 30 分钟内无法恢复，升级二线\n"
    )


def push_high_freq_to_dify() -> int:
    """将未推送的高频问题通过 Dify Dataset API 上传。"""
    config.validate_dify_dataset_config()
    rows = fetch_all(
        "SELECT id, category, sample_desc, hit_count, keyword_sig "
        "FROM high_freq_issues WHERE pushed_dify = 0"
    )
    if not rows:
        print("[推送] 无待推送的高频问题")
        return 0

    url = f"{config.DIFY_BASE_URL}/datasets/{config.DIFY_DATASET_ID}/document/create-by-text"
    headers = {
        "Authorization": f"Bearer {config.DIFY_DATASET_API_KEY}",
        "Content-Type": "application/json",
    }
    pushed = 0
    for row in rows:
        doc_name = f"高频问题_{row['category']}_{row['keyword_sig'][:8]}"
        text = _build_dify_doc_text(row["category"], row["sample_desc"], row["hit_count"])
        payload = {
            "name": doc_name,
            "text": text,
            "indexing_technique": "high_quality",
            "process_rule": {
                "mode": "automatic",
            },
        }
        resp = post_json(url, headers=headers, payload=payload, timeout=120)
        resp.raise_for_status()
        execute(
            "UPDATE high_freq_issues SET pushed_dify = 1 WHERE id = %s",
            (row["id"],),
        )
        pushed += 1
        print(f"[推送] 已上传: {doc_name}")
        time.sleep(1)  # 避免 API 限流

    return pushed


def print_order_report() -> None:
    """打印工单分类统计。"""
    stats = fetch_all(
        "SELECT fault_category, COUNT(*) AS cnt, SUM(is_duplicate) AS dup "
        "FROM work_orders GROUP BY fault_category"
    )
    print("\n【工单分类统计】")
    for s in stats:
        print(f"  {s['fault_category']}: {s['cnt']} 条 (重复 {s['dup'] or 0})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运维工单预处理")
    parser.add_argument("--classify", action="store_true", help="正则分类")
    parser.add_argument("--dedup", action="store_true", help="标记重复")
    parser.add_argument("--summary", action="store_true", help="汇总高频")
    parser.add_argument("--push-dify", action="store_true", help="推送 Dify 知识库")
    parser.add_argument("--report", action="store_true", help="打印统计")
    parser.add_argument("--all", action="store_true", help="执行全部步骤")
    args = parser.parse_args(argv)

    if not any([args.classify, args.dedup, args.summary, args.push_dify, args.report, args.all]):
        parser.print_help()
        return 1

    try:
        if args.all or args.classify:
            update_fault_categories()
        if args.all or args.dedup:
            mark_duplicate_orders()
        if args.all or args.summary:
            summarize_high_freq_issues()
        if args.all or args.push_dify:
            push_high_freq_to_dify()
        if args.all or args.report:
            print_order_report()
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
