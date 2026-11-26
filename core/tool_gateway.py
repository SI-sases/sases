"""
统一工具网关

所有工具调用必须走本网关，禁止直接 import harness_runtime 调用 invoke_tool。
当前实现路由到本地，P3 阶段扩展为跨节点 HTTP 调用，调用点零改动。
"""
import asyncio

import json
import datetime

from typing import Dict, Any

from core.harness_models import ToolInvokeResponse


def _resolve_endpoint(module_id: str) -> str:
    """解析工具端点。当前实现：全部指向本地。P3 将改为查 api_registry 表。"""
    return f"local://{module_id}"


def _invoke_local_sync(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    """本地调用（同步）。延迟 import 避免循环依赖。"""
    from core.harness_runtime import harness_runtime
    return harness_runtime.invoke_tool(module_id, params)


def _invoke_http_sync(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    """HTTP 调用（同步）。P3 才实现。"""
    raise NotImplementedError("HTTP endpoint 在 P3 才实现")



def _external_guard(module_id: str):
    """外部工具必须已安装且已启用；未启用直接给出可读错误。"""
    try:
        from core import tool_registry
    except Exception:
        return None
    entry = tool_registry.get(module_id)
    if not entry or not entry.get("external"):
        return None
    if not entry.get("enabled"):
        return ToolInvokeResponse(
            module_id=module_id,
            success=False,
            error="工具 '" + module_id + "' 已安装但未启用，请先在工具管理中启用",
        )
    return None


def _invoke_mcp_sync(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    if __import__("os").environ.get("SASES_MCP_ALLOW", "0") not in ("1", "true", "yes"):
        return ToolInvokeResponse(module_id=module_id, success=False, error="MCP client disabled")
    parts = module_id.split(".", 2)
    if len(parts) != 3:
        return ToolInvokeResponse(module_id=module_id, success=False, error="Use mcp.<server>.<tool>")
    _, server, tool = parts
    try:
        from core.services import mcp_client
        servers = mcp_client.list_servers()
        match = next((s for s in servers if str(s["id"]) == server or s["name"] == server), None)
        if not match:
            return ToolInvokeResponse(module_id=module_id, success=False, error="MCP server not found")
        result = mcp_client.call_tool(match["id"], tool, params)
        return ToolInvokeResponse(module_id=module_id, success=True, result=result)
    except Exception as exc:
        return ToolInvokeResponse(module_id=module_id, success=False, error=str(exc)[:500])


def _invoke_plugin_sync(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    parts = module_id.split(".", 1)
    if len(parts) != 2:
        return ToolInvokeResponse(module_id=module_id, success=False, error="Use plugin.<id>")
    try:
        from core.services import plugin_runtime
        result = plugin_runtime.run_tool(parts[1], params)
        return ToolInvokeResponse(module_id=module_id, success=True, result=result)
    except Exception as exc:
        return ToolInvokeResponse(module_id=module_id, success=False, error=str(exc)[:500])


def _route(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    if module_id.startswith("mcp."):
        return _invoke_mcp_sync(module_id, params)
    if module_id.startswith("plugin."):
        return _invoke_plugin_sync(module_id, params)
    _guard = _external_guard(module_id)
    if _guard:
        return _guard

    # 异步工具：提交到任务池，立即返回 handle
    try:
        from core.services import async_task_service
        if async_task_service.is_async_tool(module_id):
            return async_task_service.submit(module_id, params)
    except Exception as _e_async:
        print("[gateway] async 路由失败: " + str(_e_async))

    if module_id.startswith("ext_api_"):
        try:
            api_id = int(module_id[len("ext_api_"):])
        except Exception:
            return ToolInvokeResponse(module_id=module_id, success=False, error="Invalid ext_api format")
        return _handle_ext_api(api_id, params)

    """按 endpoint 前缀路由到本地或远程。"""
    endpoint = _resolve_endpoint(module_id)
    if endpoint.startswith("local://"):
        return _invoke_local_sync(module_id, params)
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return _invoke_http_sync(module_id, params)
    return ToolInvokeResponse(
        module_id=module_id,
        success=False,
        error=f"Unknown endpoint: {endpoint}",
    )


def invoke_tool(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    """同步入口。用于 sync 上下文。"""
    return _route(module_id, params)


async def invoke_tool_async(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
    """异步入口。用于 async 上下文，内部用 to_thread 包装同步路由。"""
    return await asyncio.to_thread(_route, module_id, params)



def _handle_ext_api(api_id: int, params: Dict[str, Any]) -> ToolInvokeResponse:
    import sqlite3
    import httpx
    import json
    
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute("SELECT endpoint, method, auth_key_encrypted FROM user_api_configs WHERE id=?", (api_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row: 
        return ToolInvokeResponse(module_id=f"ext_api_{api_id}", success=False, error="未找到该 API 配置")
        
    endpoint, method, auth_key = row
    headers = {}
    if auth_key: headers["Authorization"] = f"Bearer {auth_key}"
    m = method.upper() if method else "GET"
    
    try:
        if m == "GET":
            resp = httpx.get(endpoint, headers=headers, params=params, timeout=15, trust_env=False)
        else:
            resp = httpx.post(endpoint, headers=headers, json=params, timeout=15, trust_env=False)
        if resp.status_code >= 400:
            return ToolInvokeResponse(
                module_id=f"ext_api_{api_id}", success=False,
                error="HTTP " + str(resp.status_code) + ": " + (resp.text or "")[:200])
        return ToolInvokeResponse(module_id=f"ext_api_{api_id}", success=True, result=resp.text)
    except Exception as e:
        return ToolInvokeResponse(module_id=f"ext_api_{api_id}", success=False, error=str(e))
