"""
统一工具网关

所有工具调用必须走本网关，禁止直接 import harness_runtime 调用 invoke_tool。
当前实现路由到本地，P3 阶段扩展为跨节点 HTTP 调用，调用点零改动。
"""
import asyncio
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


