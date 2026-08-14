# -*- coding: utf-8 -*-
"""
模块 1：Dify 云端 API 调用 + 问答日志入库 MySQL

用法:
    python dify_api.py "MySQL主从延迟怎么处理"
    python dify_api.py --interactive
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from typing import Any, Optional

import config
from http_utils import post_json
from db_utils import execute, fetch_all

# Dify Chatflow 发送消息接口
CHAT_MESSAGES_URL = f"{config.DIFY_BASE_URL}/chat-messages"


def ask_dify(
    question: str,
    user_id: str = "ops-user",
    conversation_id: str = "",
    response_mode: str = "blocking",
) -> dict[str, Any]:
    """
    调用 Dify 官方 API 发送运维咨询问题，返回标准化答疑结果。

    :param question: 运维问题文本
    :param user_id: 终端用户标识（Dify 用于区分会话）
    :param conversation_id: 多轮对话时传入上一轮返回的 conversation_id
    :param response_mode: blocking 阻塞 | streaming 流式
    :return: Dify 原始 JSON 响应
    """
    config.validate_dify_app_config()

    headers = {
        "Authorization": f"Bearer {config.DIFY_APP_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {},
        "query": question,
        "response_mode": response_mode,
        "conversation_id": conversation_id or "",
        "user": user_id,
    }

    resp = post_json(CHAT_MESSAGES_URL, headers=headers, payload=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def save_qa_log(
    question: str,
    dify_response: dict[str, Any],
    user_id: str = "ops-user",
) -> int:
    """将问答记录写入 MySQL qa_logs 表。"""
    answer = dify_response.get("answer", "")
    conversation_id = dify_response.get("conversation_id", "")
    message_id = dify_response.get("message_id", "")
    retriever = dify_response.get("metadata", {}).get("retriever_resources")
    retriever_json = json.dumps(retriever, ensure_ascii=False) if retriever else None

    sql = """
        INSERT INTO qa_logs (user_id, question, answer, conversation_id, message_id, retriever_resources)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    return execute(sql, (user_id, question, answer, conversation_id, message_id, retriever_json))


def chat_and_log(question: str, user_id: str = "ops-user") -> dict[str, Any]:
    """一站式：提问 + 入库 + 返回结果。"""
    result = ask_dify(question, user_id=user_id)
    save_qa_log(question, result, user_id=user_id)
    return result


def list_recent_logs(limit: int = 10) -> list[dict]:
    """查询最近问答日志。"""
    return fetch_all(
        "SELECT id, user_id, question, LEFT(answer, 200) AS answer_preview, created_at "
        "FROM qa_logs ORDER BY id DESC LIMIT %s",
        (limit,),
    )


def _print_result(result: dict[str, Any]) -> None:
    print("=" * 60)
    print("【AI 回答】")
    print(result.get("answer", ""))
    print("-" * 60)
    print(f"conversation_id: {result.get('conversation_id', '')}")
    resources = result.get("metadata", {}).get("retriever_resources") or []
    if resources:
        print(f"引用片段数: {len(resources)}")
    print("=" * 60)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Dify 运维答疑 API 调用")
    parser.add_argument("question", nargs="?", help="运维咨询问题")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--user", default="ops-user", help="用户标识")
    parser.add_argument("--list-logs", action="store_true", help="查看最近问答日志")
    args = parser.parse_args(argv)

    if args.list_logs:
        for row in list_recent_logs():
            print(f"[{row['created_at']}] {row['question'][:40]}...")
        return 0

    if args.interactive:
        user_id = args.user or f"user-{uuid.uuid4().hex[:8]}"
        print("进入交互模式，输入 quit 退出")
        while True:
            try:
                q = input("\n运维问题> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not q or q.lower() in {"quit", "exit", "q"}:
                break
            try:
                result = chat_and_log(q, user_id=user_id)
                _print_result(result)
            except Exception as exc:
                print(f"错误: {exc}", file=sys.stderr)
        return 0

    if not args.question:
        parser.print_help()
        return 1

    result = chat_and_log(args.question, user_id=args.user)
    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
