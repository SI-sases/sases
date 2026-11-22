import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run(params):
    goal = str((params or {}).get("goal") or "").strip()
    if not goal:
        return {"success": False, "error": "goal 不能为空"}
    from core.services.run_context import get_current
    ctx = get_current()
    if not ctx.get("user_id") or not ctx.get("conversation_id"):
        return {"success": False, "error": "缺少父 run 上下文"}
    try:
        from core.services import message_service, run_service
        cid = message_service.create_conversation(ctx["user_id"], None, "子任务")
        rid = run_service.create_run(ctx["user_id"], cid, "subagent", goal,
                                     supervisor_id="sases_assistant")
        result = asyncio.run(run_service.run_once(
            ctx["user_id"], cid, goal, source="subagent",
            max_steps=min(int((params or {}).get("max_steps") or 4), 6),
            run_id=rid, finish=True,
            allowed_tool_ids=["file_read", "grep_code", "dir_tree"],
        ))
        loop = (result or {}).get("loop") or {}
        return {"success": str(result.get("status")) == "completed",
                "run_id": rid, "child_conversation_id": cid,
                "result": str(loop.get("content") or "")[:4000]}
    except Exception as e:
        return {"success": False, "error": str(e)}
