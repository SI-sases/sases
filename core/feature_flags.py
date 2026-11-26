"""Temporary feature flags."""
from __future__ import annotations

import os


def wisdom_enabled() -> bool:
    """智维空间入口。默认关闭，不对客户端开放。"""
    return os.environ.get("SASES_ZHIWEI_ENABLED", "0") in ("1", "true", "yes")
