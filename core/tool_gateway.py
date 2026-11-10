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



def _route(module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
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



def _handle_ext_api(api_id: int, params: Dict[str, Any]) -> Any:
    import sqlite3
    import httpx
    from core.harness_models import ToolInvokeResponse
    
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute("SELECT endpoint, method, auth_key_encrypted FROM user_api_configs WHERE id=?", (api_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row: 
        return ToolInvokeResponse(module_id=f"ext_api_{api_id}", success=False, error="未找到该外部 API")
        
    endpoint, method, auth_key = row
    headers = {}
    if auth_key: headers["Authorization"] = f"Bearer {auth_key}"
    m = method.upper() if method else "GET"
    
    try:
        # 加上 User-Agent 防屏蔽
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        if m == "GET":
            resp = httpx.get(endpoint, headers=headers, params=params, timeout=15)
        else:
            resp = httpx.post(endpoint, headers=headers, json=params, timeout=15)
            
        # 强行包成对象返回
        return ToolInvokeResponse(module_id=f"ext_api_{api_id}", success=True, result=resp.text)
    except Exception as e:
        return ToolInvokeResponse(module_id=f"ext_api_{api_id}", success=False, error=str(e))
