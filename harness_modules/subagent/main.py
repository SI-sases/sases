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
        from core.db import db_cursor
        from core.services import agent_loop
        with db_cursor(commit=True) as cur:
            cur.execute("INSERT INTO conversations (user_id,title) VALUES (?,?)",
                        (ctx["user_id"], "子任务"))
            cid = cur.lastrowid
            cur.execute("INSERT INTO supervisor_runs (user_id,conversation_id,supervisor_id,goal,status,"
                        "current_round,max_rounds,history,task_type) VALUES (?,?,?,?,'running',0,1,'[]','subagent')",
                        (ctx["user_id"], cid, "sases_assistant", goal))
            rid = cur.lastrowid
        loop = asyncio.run(agent_loop.run(
            ctx["user_id"], cid, goal, max_steps=min(int((params or {}).get("max_steps") or 4), 6),
            run_id=rid, mode="strict",
            allowed_tool_ids=["file_read", "grep_code", "dir_tree"],
        ))
        with db_cursor(commit=True) as cur:
            cur.execute("UPDATE supervisor_runs SET status=?, finished_at=datetime('now') WHERE id=?",
                        ("completed" if loop.get("status") == "ok" else "failed", rid))
        return {"success": loop.get("status") == "ok",
                "run_id": rid, "child_conversation_id": cid,
                "result": str(loop.get("content") or "")[:4000]}
    except Exception as e:
        return {"success": False, "error": str(e)}
