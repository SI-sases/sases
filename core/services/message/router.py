# core/services/message/router.py
# -*- coding: utf-8 -*-
"""D: 消息入口的轻量路由：前缀归一 + fast 判定。"""
import re


def normalize_prefix(content):
    """把 #N xxx / #N：xxx / #N:xxx 统一成 #N:xxx；*0/*1 同理。"""
    if not content or not isinstance(content, str):
        return content
    s = content.strip()
    m = re.match(r'^([#*][0-4])(?![0-9a-zA-Z])', s)
    if m:
        prefix = m.group(1)
        rest = s[len(prefix):].lstrip('：: ' + chr(9))
        return prefix + ':' + rest
    return content


def should_fast(agent_mode, content, enabled_tool_ids=None):
    """B2: 决定是否走 fast 单 Agent；保守策略，失败会自动回退 strict。"""
    mode = (agent_mode or "").strip().lower()
    if mode == "strict":
        return False
    if mode == "fast":
        return True
    s = (content or "").strip()
    if not s or s.startswith("#"):
        return False
    if len(s) > 300:
        return False
    _heavy = ("改", "实现", "修复", "迁移", "重构", "批量", "部署", "发布", "删除", "所有文件")
    if any(k in s for k in _heavy):
        return False
    return True
