"""core/hive/client.py —— 蜂巢出站请求 helper（自动带 token）。"""
from core.hive.config import HIVE_TOKEN


def hive_headers():
    if HIVE_TOKEN:
        return {"Authorization": f"Bearer {HIVE_TOKEN}"}
    return {}
