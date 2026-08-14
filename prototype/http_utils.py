# -*- coding: utf-8 -*-
"""HTTP 请求工具：调用 Dify API 时绕过系统代理，避免 WinError 10053。"""

from __future__ import annotations

from typing import Any, Optional

import requests


# 直连 Dify / 硅基流动，不走系统 HTTP 代理
NO_PROXY = {"http": None, "https": None}


def post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int = 120,
) -> requests.Response:
    session = requests.Session()
    session.trust_env = False
    return session.post(url, headers=headers, json=payload, timeout=timeout, proxies=NO_PROXY)


def get_json(
    url: str,
    headers: dict[str, str],
    timeout: int = 60,
    params: Optional[dict] = None,
) -> requests.Response:
    session = requests.Session()
    session.trust_env = False
    return session.get(url, headers=headers, params=params, timeout=timeout, proxies=NO_PROXY)
