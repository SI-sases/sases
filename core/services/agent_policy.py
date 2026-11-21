# core/services/agent_policy.py
# -*- coding: utf-8 -*-
"""A1: agent loop 的策略钩子（审批/检查点/轨迹）。"""
WRITE_TOOLS = {"file_write", "smart_edit", "file_replace_range", "delete_block",
               "split_block", "git_ops"}


async def before_tool(user_id, conversation_id, run_id, step, tool, args):
    try:
        if run_id and tool in WRITE_TOOLS and isinstance(args, dict):
            fp = args.get("file_path")
            if fp:
                from . import checkpoint_service
                checkpoint_service.snapshot(run_id, str(step), fp)
    except Exception as e:
        print("[policy] checkpoint 失败: " + str(e))
    try:
        if run_id:
            from . import trace_service
            trace_service.emit(run_id, conversation_id, 2, "tool_start",
                               content="调用 " + str(tool), tool=str(tool), status="running")
    except Exception:
        pass


async def after_tool(user_id, conversation_id, run_id, step, tool, args, ok, text):
    try:
        if run_id:
            from . import trace_service
            trace_service.emit(run_id, conversation_id, 2, "tool_done",
                               content=str(text)[:500], tool=str(tool),
                               status="success" if ok else "failed")
    except Exception:
        pass
