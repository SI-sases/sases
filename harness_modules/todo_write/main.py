# harness_modules/todo_write/main.py
# -*- coding: utf-8 -*-
"""todo_write 由 agent_loop 拦截；直接网关调用只返回提示。"""


def run(params):
    return {
        "success": False,
        "error": "todo_write 必须在 agent_loop 内调用（需要当前会话/run 上下文）",
    }
