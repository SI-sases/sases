"""Expose the existing SASES MCP client to the main AGI, disabled by default."""
from __future__ import annotations

import os


def enabled() -> bool:
    return os.environ.get("SASES_MCP_ALLOW", "0") == "1"


def list_servers() -> dict:
    if not enabled():
        return {"ok": False, "error": "MCP client disabled; set SASES_MCP_ALLOW=1"}
    from core.services import mcp_client
    return {"ok": True, "servers": mcp_client.list_servers()}


def list_tools(server_id: int) -> dict:
    if not enabled():
        return {"ok": False, "error": "MCP client disabled; set SASES_MCP_ALLOW=1"}
    from core.services import mcp_client
    return {"ok": True, "tools": mcp_client.list_tools(server_id)}


def call(server_id: int, tool: str, arguments: dict | None = None) -> dict:
    if not enabled():
        return {"ok": False, "error": "MCP client disabled; set SASES_MCP_ALLOW=1"}
    from core.services import mcp_client
    return {"ok": True, "result": mcp_client.call_tool(server_id, tool, arguments or {})}
