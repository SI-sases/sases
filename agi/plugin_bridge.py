"""Expose the existing plugin runtime to the main AGI, disabled by default."""
from __future__ import annotations

import os


def enabled() -> bool:
    return os.environ.get("SASES_PLUGIN_ALLOW", "0") in ("1", "true", "yes")


def list_plugins() -> dict:
    if not enabled():
        return {"ok": False, "error": "plugin runtime disabled; set SASES_PLUGIN_ALLOW=1"}
    from core.services import plugin_registry
    return {"ok": True, "plugins": plugin_registry.list_plugins()}


def run_tool(plugin_id: str, params: dict | None = None) -> dict:
    if not enabled():
        return {"ok": False, "error": "plugin runtime disabled; set SASES_PLUGIN_ALLOW=1"}
    from core.services import plugin_runtime
    try:
        return {"ok": True, "result": plugin_runtime.run_tool(plugin_id, params or {})}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
