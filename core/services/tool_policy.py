"""Central tool risk and approval policy."""
from __future__ import annotations

import os

READ_TOOLS = {"file_read", "dir_list", "grep_code", "web_search", "web_fetch"}
WRITE_TOOLS = {
    "file_write", "smart_edit", "file_replace_range", "delete_block",
    "split_block", "git_ops",
}
NETWORK_TOOLS = {"web_fetch", "api_call", "http_async", "ssh_exec"}
SHELL_TOOLS = {"run_python", "run_forever", "run_command", "bash", "shell"}
MCP_PREFIX = "mcp."
PLUGIN_PREFIX = "plugin."


def is_mcp(tool: str) -> bool:
    return (tool or "").startswith(MCP_PREFIX)


def is_plugin(tool: str) -> bool:
    return (tool or "").startswith(PLUGIN_PREFIX)


def risk(tool: str, args: dict | None = None) -> str:
    tool = tool or ""
    if is_mcp(tool) or is_plugin(tool):
        return "high"
    if tool in SHELL_TOOLS or tool == "ssh_exec":
        return "high"
    if tool in WRITE_TOOLS:
        return "write"
    if tool in NETWORK_TOOLS:
        return "network"
    if tool in READ_TOOLS:
        return "read"
    return "unknown"


def requires_approval(tool: str, args: dict | None = None) -> bool:
    mode = os.getenv("SASES_APPROVAL_MODE", "risk").strip().lower()
    if mode == "off":
        return False
    if os.getenv("SASES_REQUIRE_APPROVAL") == "1":
        return True
    return risk(tool, args) in ("high", "write", "network")
