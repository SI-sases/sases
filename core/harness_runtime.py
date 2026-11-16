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
            if manifest.id == 'file_patch':
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
                'duration_ms': duration_ms,
                'error': str(error) if error else None,
            }
            _log_path = _os.path.join(_dir, 'harness_usage.log')
            with open(_log_path, 'a', encoding='utf-8') as _f:
                _f.write(_js.dumps(_entry, ensure_ascii=False) + '\n')
        except Exception:
            pass

    def _circuit_check(self, module_id: str) -> Optional[str]:
        """v0.19: 熔断器检查"""
        import time as _time
        state = self._circuit_state.get(module_id)
        if not state:
            return None
        if state.get('open'):
            elapsed = _time.time() - state.get('opened_at', 0)
            if elapsed < self._circuit_cooldown_sec:
                return f"模块 '{module_id}' 处于熔断状态，请 {int(self._circuit_cooldown_sec - elapsed)} 秒后重试"
            # 冷却结束，半开
            state['open'] = False
            state['fail_count'] = 0
        return None

    def _circuit_record(self, module_id: str, success: bool):
        """v0.19: 熔断器记录"""
        import time as _time
        state = self._circuit_state.setdefault(module_id, {'fail_count': 0, 'open': False})
        if success:
            state['fail_count'] = 0
            state['open'] = False
        else:
            state['fail_count'] = state.get('fail_count', 0) + 1
            if state['fail_count'] >= self._circuit_fail_threshold:
                state['open'] = True
                state['opened_at'] = _time.time()

    def invoke_tool(self, module_id: str, params: Optional[Dict[str, Any]] = None) -> ToolInvokeResponse:
        """v0.19: 调用工具"""
        import time as _time
        params = params or {}
        start = _time.time()

        # 熔断检查
        circuit_err = self._circuit_check(module_id)
        if circuit_err:
            return ToolInvokeResponse(
                success=False,
                module_id=module_id,
                error=circuit_err,
                duration_ms=0,
            )

        info = self._modules.get(module_id)
        if not info:
            # 尝试通过别名查找
            for mid, minfo in self._modules.items():
                m = minfo.get('manifest')
                if m and module_id in (getattr(m, 'aliases', []) or []):
                    info = minfo
                    break

        if not info:
            err = f"未找到模块 '{module_id}'"
            self._circuit_record(module_id, False)
            self._log_tool_usage(module_id, params, False, 0, err)
            return ToolInvokeResponse(
                success=False,
                module_id=module_id,
                error=err,
                duration_ms=0,
            )

        manifest = info.get('manifest')
        handler = info.get('handler') or info.get('invoke') or info.get('callable') or info.get('run_fn')

        # 权限检查
        if manifest:
            perm_err = self._check_permissions(manifest)
            if perm_err:
                duration_ms = int((_time.time() - start) * 1000)
                self._log_tool_usage(module_id, params, False, duration_ms, perm_err)
                return ToolInvokeResponse(
                    success=False,
                    module_id=module_id,
                    error=perm_err,
                    duration_ms=duration_ms,
                )

        if not handler:
            err = f"模块 '{module_id}' 没有可调用的 handler"
            self._circuit_record(module_id, False)
            duration_ms = int((_time.time() - start) * 1000)
            self._log_tool_usage(module_id, params, False, duration_ms, err)
            return ToolInvokeResponse(
                success=False,
                module_id=module_id,
                error=err,
                duration_ms=duration_ms,
            )

        try:
            result = handler(params)
            duration_ms = int((_time.time() - start) * 1000)
            self._circuit_record(module_id, True)
            self._log_tool_usage(module_id, params, True, duration_ms)
            return ToolInvokeResponse(
                success=True,
                module_id=module_id,
                result=result,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((_time.time() - start) * 1000)
            self._circuit_record(module_id, False)
            self._log_tool_usage(module_id, params, False, duration_ms, e)
            return ToolInvokeResponse(
                success=False,
                module_id=module_id,
                error=str(e),
                duration_ms=duration_ms,
            )


# 全局默认 runtime 实例
_default_runtime = None


def get_runtime() -> HarnessRuntime:
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = HarnessRuntime()
    return _default_runtime


def invoke_tool(module_id: str, params: Optional[Dict[str, Any]] = None) -> ToolInvokeResponse:
    """模块级 invoke_tool 便捷函数"""
    return get_runtime().invoke_tool(module_id, params)


def list_tools() -> List[ToolDefinition]:
    """模块级 list_tools 便捷函数"""
    return get_runtime().list_tools()


def reload_modules() -> Dict[str, Any]:
    """模块级 reload_modules 便捷函数"""
    return get_runtime().reload_modules()
harness_runtime = HarnessRuntime()
