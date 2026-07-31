# -*- coding: utf-8 -*-
"""MySQL 连接与通用数据库操作。"""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Optional

import pymysql
from pymysql.cursors import DictCursor

import config


class DatabaseError(Exception):
    """数据库相关错误。"""


@contextmanager
def get_connection(use_database: bool = True) -> Generator[pymysql.Connection, None, None]:
    """
    获取 MySQL 连接上下文。
    use_database=False 时仅连服务器（用于首次建库）。
    """
    params: dict[str, Any] = {
        "host": config.MYSQL_HOST,
        "port": config.MYSQL_PORT,
        "user": config.MYSQL_USER,
        "password": config.MYSQL_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": True,
    }
    if use_database:
        params["database"] = config.MYSQL_DATABASE

    conn = pymysql.connect(**params)
    try:
        yield conn
    finally:
        conn.close()


def execute_sql_file(sql_path: str, use_database: bool = False) -> None:
    """执行 SQL 文件（按分号拆分语句）。"""
    path = config.SQL_DIR / sql_path if not sql_path.startswith("/") else sql_path
    text = open(path, encoding="utf-8").read()
    # 去掉单行注释
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    statements = [s.strip() for s in re.split(r";\s*\n", cleaned) if s.strip()]

    with get_connection(use_database=use_database) as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)


def fetch_all(sql: str, args: Optional[tuple | list] = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            return list(cur.fetchall())


def fetch_one(sql: str, args: Optional[tuple | list] = None) -> Optional[dict]:
    rows = fetch_all(sql, args)
    return rows[0] if rows else None


def execute(sql: str, args: Optional[tuple | list] = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute(sql, args or ())


def executemany(sql: str, args_list: Iterable[tuple | list]) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            return cur.executemany(sql, list(args_list))
