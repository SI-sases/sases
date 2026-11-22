# core/services/continuation_service.py
# -*- coding: utf-8 -*-
"""把“继续 / 按建议执行”这类无目标消息转成可执行目标。"""
import re

_EXACT = {
    "继续", "继续执行", "继续吧", "接着来", "接着做", "下一步", "下一步吧",
    "按建议执行", "按建议和优先级执行", "按优先级执行", "按推荐和建议执行",
    "按推荐执行", "按优先级", "按建议", "执行", "开始", "开始执行", "go", "continue",
}
_PREFIX = ("按建议", "按推荐", "按优先级", "继续", "接着", "下一步")


def is_continue(text):
    s = re.sub(r"[\s，。！？,.!?：:；;]+", "", str(text or "")).lower()
    if not s:
        return False
    if s in _EXACT:
        return True
    return len(s) <= 12 and any(s.startswith(p) for p in _PREFIX)


def rewrite(text):
    if not is_continue(text):
        return text
    return ("继续执行上一条回复中提出的建议/下一步，按优先级自行选择并直接落地；"
            "如果上一条已经完成，选择最有价值的下一项继续，不要问用户“继续什么”，"
            "也不要只给方案。优先完成当前未完成的 todo。")
