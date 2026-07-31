# -*- coding: utf-8 -*-
"""初始化 MySQL 数据库：建库建表 + 导入 sql/init.sql"""

from __future__ import annotations

import sys
from pathlib import Path

import pymysql

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from db_utils import execute_sql_file  # noqa: E402


def init_database() -> None:
    if not config.MYSQL_PASSWORD or "在此填写" in config.MYSQL_PASSWORD:
        raise ValueError("请先在 .env 中设置 MYSQL_PASSWORD")

    print(f"连接 MySQL {config.MYSQL_HOST}:{config.MYSQL_PORT} ...")
    conn = pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
    )
    conn.close()

    sql_file = config.SQL_DIR / "init.sql"
    print(f"执行 {sql_file} ...")
    execute_sql_file("init.sql", use_database=False)
    print("数据库初始化完成！")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as exc:
        print(f"初始化失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
