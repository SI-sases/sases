"""统一任务调度引擎：解耦聊天触发与底层三者执行。"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _check_concurrency_and_budget(user_id: int):
    """全局并发控制 / API 预算限制检查。返回 (ok, reason)。"""
    try:
        from . import supervisor_service
        checker = getattr(supervisor_service, "check_concurrency_and_budget", None)
        if checker is None:
            return True, ""
        return checker(user_id)
    except Exception as exc:  # pragma: no cover
        logger.warning("并发/预算检查异常，放行: %s", exc)
        return True, ""


def dispatch_task(user_id: int, goal: str, context_type: str = "chat",
                  context_id: str = None, attachments: list = None):
    """统一入口：把一次任务派发给调度员。"""
    ok, reason = _check_concurrency_and_budget(user_id)
    if not ok:
        return {"ok": False, "error": reason or "并发或预算受限"}

    from . import supervisor_service

    kwargs = {
        "user_id": user_id,
        "goal": goal,
        "context_type": context_type,
        "context_id": context_id,
        "attachments": attachments or [],
    }

    for name in ("create_run", "plan_task"):
        fn = getattr(supervisor_service, name, None)
        if fn is None:
            continue
        try:
            result = fn(**kwargs)
        except TypeError:
            result = fn(user_id, goal)
        return {"ok": True, "result": result}

    return {"ok": False, "error": "supervisor_service 中未找到 create_run / plan_task"}
