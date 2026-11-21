# core/services/intent_service.py
# -*- coding: utf-8 -*-
"""UX-1: 轻量意图识别，让用户不用记 # 前缀。"""
import re

_TASK_WORDS = ("改", "实现", "修复", "重构", "迁移", "部署", "删除", "写入", "加一个", "优化", "替换")
_SETTING_WORDS = ("以后都", "关闭联网", "打开联网", "允许改文件", "禁止改文件", "设置")

_DAILY_RE = re.compile(r"^(?:每天|每日)\s*(\d{1,2})\s*点(?:(\d{1,2})\s*分)?\s*(.+)$")
_WEEKLY_RE = re.compile(r"^每周([一二三四五六日天])\s*(\d{1,2})\s*点(?:(\d{1,2})\s*分)?\s*(.+)$")
_WEEK_MAP = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}


def route_intent(content: str) -> dict:
    s = (content or "").strip()
    if not s:
        return {"intent": "chat", "mode": "fast", "confidence": 0.5, "reason": "empty"}

    m = _DAILY_RE.match(s)
    if m:
        h = int(m.group(1))
        minute = int(m.group(2) or 0)
        task = m.group(3).strip()
        if 0 <= h <= 23 and 0 <= minute <= 59 and task:
            return {"intent": "schedule", "mode": "strict", "confidence": 0.95,
                    "normalized": "每天%d点%d分 %s" % (h, minute, task)}

    m = _WEEKLY_RE.match(s)
    if m:
        wd = _WEEK_MAP.get(m.group(1), 0)
        h = int(m.group(2))
        minute = int(m.group(3) or 0)
        task = m.group(4).strip()
        if 0 <= h <= 23 and task:
            return {"intent": "schedule", "mode": "strict", "confidence": 0.9,
                    "normalized": None, "weekly": {"weekday": wd, "hour": h, "minute": minute, "task": task}}

    if any(k in s for k in _SETTING_WORDS):
        return {"intent": "setting", "mode": "fast", "confidence": 0.7, "reason": "setting words"}

    if any(k in s for k in _TASK_WORDS):
        return {"intent": "task", "mode": "auto", "confidence": 0.8, "reason": "task words"}

    return {"intent": "chat", "mode": "fast", "confidence": 0.6, "reason": "default"}
