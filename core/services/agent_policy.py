# core/services/agent_policy.py
# -*- coding: utf-8 -*-
"""A1: agent loop 的策略钩子（审批/检查点/轨迹）。"""
WRITE_TOOLS = {"file_write", "smart_edit", "file_replace_range", "delete_block",
               "split_block", "git_ops"}
NETWORK_TOOLS = {"web_fetch", "api_call", "http_async", "ssh_exec"}
_HIGH_RISK_TOOLS = {"delete_block", "split_block", "git_ops", "ssh_exec"}


def _is_high_risk(tool, args):
    import os
    if tool in _HIGH_RISK_TOOLS:
        return True
    if tool == "run_python":
        code = str((args or {}).get("code") or "")
        return any(x in code for x in ("os.remove", "shutil.rmtree", "rm -rf",
                                       "unlink(", "DROP TABLE", "DELETE FROM"))
    if tool not in WRITE_TOOLS or not isinstance(args, dict):
        return False
    fp = str(args.get("file_path") or "")
    if not fp:
        return True
    root = os.path.realpath(os.getcwd())
    real = os.path.realpath(fp)
    try:
        rel = os.path.relpath(real, root).replace("\\", "/")
    except Exception:
        return True
    if rel.startswith("..") or os.path.isabs(rel):
        return True
    if any(rel == x or rel.startswith(x + "/") for x in
           ("core", "scripts", "launcher", "build_portable", ".git")):
        return True
    if rel in ("app_full.py", "requirements.txt", "users.db", ".env") or "secret" in rel.lower():
        return True
    return False


class ApprovalRequired(Exception):
    def __init__(self, step, tool):
        self.step = step
        self.tool = tool
        super().__init__("awaiting approval: " + str(tool))


async def before_tool(user_id, conversation_id, run_id, step, tool, args):
    import os
    try:
        from . import tool_policy
        _need = bool(run_id) and tool_policy.requires_approval(tool, args)
        if run_id and _need:
            from . import approval_service
            if not approval_service.is_approved(run_id, str(step), {"step": step, "module_id": tool}):
                await approval_service.request_approval(run_id, str(step),
                                                        {"step": step, "module_id": tool},
                                                        conversation_id, user_id)
                raise ApprovalRequired(step, tool)
    except ApprovalRequired:
        raise
    except Exception as e:
        print("[policy] approval 检查失败: " + str(e))
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
