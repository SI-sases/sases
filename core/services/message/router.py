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
    """C4: 默认 fast；只有显式 strict / 高风险才走四角色。"""
    mode = (agent_mode or "").strip().lower()
    if mode == "strict":
        return False
    if mode == "fast":
        return True
    s = (content or "").strip()
    if not s or s.startswith("#"):
        return False
    if any(k in s for k in ("严格", "四角色", "strict", "Strict")):
        return False
    if any(k in s for k in ("批量", "所有文件", "部署", "发布", "迁移", "删库")):
        return False
    if len(s) > 800:
        return False
    return True
