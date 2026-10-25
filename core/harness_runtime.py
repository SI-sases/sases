# core/harness_runtime.py
from typing import Dict, Any, List, Optional

from core.harness_loader import load_harness_modules, HARNESS_MODULES_DIR
from core.harness_models import ModuleManifest, ToolDefinition, ToolInvokeResponse

# 默认允许的权限集合（安全权限）
DEFAULT_ALLOWED_PERMISSIONS = {
    "calculation",
    "text_processing",
    "json_formatting",
    "string_utils",
    "unit_conversion",
    "base64_codec",
    "text_stats",
    "file_patch",
    "frontend_edit",
    "restricted_file_write",
    "network",
    "llm_call",
    "file_read"
}

# 危险权限，默认拒绝，需要用户显式授权
DANGEROUS_PERMISSIONS = set()  # v0.19: 本地系统，权限全开

# 供未来分发时启用：设 SASES_HARNESS_STRICT=1 环境变量恢复限制
_STRICT_SET = {
    "local_command",
    "file_write",
    "file_delete",
    "network",
    "socket",
    "subprocess",
    "system"
}
import os as _os
if _os.environ.get('SASES_HARNESS_STRICT') == '1':
    DANGEROUS_PERMISSIONS = _STRICT_SET


class HarnessRuntime:
    def __init__(self, modules_dir: str = HARNESS_MODULES_DIR):
        self.modules_dir = modules_dir
        self._modules = load_harness_modules(modules_dir)
        self.user_grants = set()
        # v0.19: 熔断器
        self._circuit_state = {}
        self._circuit_fail_threshold = 5
        self._circuit_cooldown_sec = 300

    def _detect_conflicts(self, modules):
        """v0.19: 只检测不同工具之间 id 重复（忽略别名）"""
        seen = {}
        dup = []
        for k, info in modules.items():
            m = info.get('manifest')
            if not m:
                continue
            mid = getattr(m, 'id', '')
            if mid in seen:
                # 同一 manifest 对象 = 别名，跳过
                if seen[mid] is not m:
                    dup.append(mid)
            else:
                seen[mid] = m
        return dup

    def reload_modules(self) -> Dict[str, Any]:
        """
        重新扫描模块目录，动态加载新生成的 Harness 模块。
        返回加载结果报告。
        """
        old_ids = set(self._modules.keys())
        self._modules = load_harness_modules(self.modules_dir)
        new_ids = set(self._modules.keys())

        added = list(new_ids - old_ids)
        removed = list(old_ids - new_ids)
        total = len(new_ids)

        _conflicts = self._detect_conflicts(self._modules)
        for _w in _conflicts:
            print('[harness] 冲突警告: ' + _w)
        return {
            "success": True,
            "total_modules": total,
            "added": added,
            "removed": removed,
            "added_count": len(added),
            "removed_count": len(removed),
            "conflicts": _conflicts
        }

    def list_tools(self) -> List[ToolDefinition]:
        tools = []
        _seen = set()
        for module_id, info in self._modules.items():
            manifest = info["manifest"]
            if manifest.id in _seen:
                continue
            _seen.add(manifest.id)
            tools.append(ToolDefinition(
                module_id=manifest.id,
                name=manifest.name,
                description=manifest.description,
                capabilities=manifest.capabilities,
                permissions=manifest.permissions,
                version=manifest.version,
                node_type=manifest.node_type,
                aliases=list(getattr(manifest, 'aliases', []) or []),
                params=dict(getattr(manifest, 'params', {}) or {}),
                cost=dict(getattr(manifest, 'cost', {}) or {}),
            ))
        return tools

    def get_tool(self, module_id: str) -> Optional[ToolDefinition]:
        for tool in self.list_tools():
            if tool.module_id == module_id:
                return tool
        return None

    def _check_permissions(self, manifest: ModuleManifest) -> Optional[str]:
        # v0.19: 本地系统，权限检查全放开
        # 如需恢复限制：设 SASES_HARNESS_STRICT=1 环境变量
        import os as _os
        if _os.environ.get('SASES_HARNESS_STRICT') == '1':
            for perm in manifest.permissions:
                if perm in self.user_grants:
                    continue
                if perm in DANGEROUS_PERMISSIONS:
                    return f"模块 '{manifest.name}' 需要危险权限 '{perm}'，但当前未被授权，已阻止执行"
                if perm not in DEFAULT_ALLOWED_PERMISSIONS:
                    return f"模块 '{manifest.name}' 声明了未知权限 '{perm}'，已阻止执行"
        return None

    def _log_tool_usage(self, module_id, params, success, duration_ms, error=None):
        """v0.19: 记录每次工具调用"""
        try:
            import json as _js
            from datetime import datetime as _dt
            import os as _os
            _dir = 'data'
            _os.makedirs(_dir, exist_ok=True)
            _entry = {
                'ts': _dt.now().isoformat(),
                'module_id': module_id,
                'success': bool(success),
                'duration_ms': int(duration_ms),
                'error': (error or '')[:200],
                'params_keys': list(params.keys()) if isinstance(params, dict) else [],
            }
            with open(_os.path.join(_dir, 'tool_usage.jsonl'), 'a', encoding='utf-8') as _f:
                _f.write(_js.dumps(_entry, ensure_ascii=False) + chr(10))
        except Exception:
            pass

    def invoke_tool(self, module_id: str, params: Dict[str, Any]) -> ToolInvokeResponse:
        import time as _t2
        _start = _t2.time()
        info = self._modules.get(module_id)
        if not info:
            self._log_tool_usage(module_id, params, False, 0, 'Module not found')
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=f"Module {module_id} not found"
            )

        manifest = info["manifest"]

        perm_error = self._check_permissions(manifest)
        if perm_error:
            self._log_tool_usage(module_id, params, False, 0, perm_error)
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=perm_error
            )

        try:
            result = info["run_fn"](params)
            _dur = int((_t2.time() - _start) * 1000)
            self._log_tool_usage(module_id, params, True, _dur)
            return ToolInvokeResponse(
                module_id=module_id,
                success=True,
                result=result
            )
        except Exception as e:
            _dur = int((_t2.time() - _start) * 1000)
            self._log_tool_usage(module_id, params, False, _dur, str(e))
            return ToolInvokeResponse(
                module_id=module_id,
                success=False,
                error=str(e)
            )

    def grant_permission(self, module_id: str, permission: str):
        """用户授权某个模块的某个权限"""
        self.user_grants.add(permission)

    def revoke_permission(self, module_id: str, permission: str):
        """撤销授权"""
        self.user_grants.discard(permission)

    def get_node_info(self, module_id: str) -> Optional[dict]:
        info = self._modules.get(module_id)
        if not info:
            return None
        manifest = info["manifest"]
        return {
            "node_id": manifest.id,
            "name": manifest.name,
            "description": manifest.description,
            "node_type": manifest.node_type,
            "capabilities": manifest.capabilities,
            "icon": manifest.icon
        }


# 全局单例
harness_runtime = HarnessRuntime()
