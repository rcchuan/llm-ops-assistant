# -*- coding: utf-8 -*-
"""统一加载 .env 配置，供各模块引用。"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录下的 .env
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ---------- Dify 云端 API ----------
DIFY_BASE_URL = _get("DIFY_BASE_URL", "https://api.dify.ai/v1").rstrip("/")
DIFY_APP_API_KEY = _get("DIFY_APP_API_KEY")
DIFY_DATASET_API_KEY = _get("DIFY_DATASET_API_KEY")
DIFY_DATASET_ID = _get("DIFY_DATASET_ID")

# ---------- MySQL ----------
MYSQL_HOST = _get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(_get("MYSQL_PORT", "3306") or "3306")
MYSQL_USER = _get("MYSQL_USER", "root")
MYSQL_PASSWORD = _get("MYSQL_PASSWORD")
MYSQL_DATABASE = _get("MYSQL_DATABASE", "dify_ops")

# ---------- Flask ----------
FLASK_HOST = _get("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(_get("FLASK_PORT", "5000") or "5000")

# ---------- 路径 ----------
DATA_DIR = _ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
RAW_CORPUS_DIR = DATA_DIR / "corpus" / "raw"
SQL_DIR = _ROOT / "sql"


def mysql_config() -> dict:
    """返回 pymysql 连接参数字典。"""
    return {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": MYSQL_DATABASE,
        "charset": "utf8mb4",
        "autocommit": True,
    }


def validate_dify_app_config() -> None:
    if not DIFY_APP_API_KEY:
        raise ValueError("请在 .env 中设置 DIFY_APP_API_KEY")


def validate_dify_dataset_config() -> None:
    if not DIFY_DATASET_API_KEY or not DIFY_DATASET_ID:
        raise ValueError("请在 .env 中设置 DIFY_DATASET_API_KEY 与 DIFY_DATASET_ID")
