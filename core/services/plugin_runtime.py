"""Opt-in tool plugin runtime.

Contract: ``python <entrypoint>`` reads JSON params from stdin, writes JSON to
stdout, exits 0. Runs in a short-lived subprocess with a timeout.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from core.services import plugin_registry

ROOT = plugin_registry.PLUGINS


def _allowed() -> bool:
    return os.environ.get("SASES_PLUGIN_ALLOW", "0") in ("1", "true", "yes")


def run_tool(plugin_id: str, params: dict | None = None, timeout: int = 20) -> dict:
    if not _allowed():
        raise RuntimeError("plugin tools disabled; set SASES_PLUGIN_ALLOW=1")
    plugin = plugin_registry.get_plugin(plugin_id)
    if not plugin.get("enabled"):
        raise RuntimeError("plugin disabled")
    manifest = plugin_registry.get_manifest(plugin_id)
    if manifest.get("type") != "tool":
        raise RuntimeError("not a tool plugin")
    entry = manifest.get("entrypoint")
    if not entry:
        raise RuntimeError("entrypoint missing")
    path = (ROOT / plugin_id / entry).resolve()
    if ROOT.resolve() not in path.parents or not path.is_file() or path.suffix != ".py":
        raise RuntimeError("invalid entrypoint")
    base_env = {k: v for k, v in os.environ.items()
                if k in ("PATH", "PYTHONPATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "LANG")}
    base_env["SASES_PLUGIN_ID"] = plugin_id
    proc = subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(params or {}, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8",
        cwd=str(ROOT / plugin_id), timeout=timeout,
        env=base_env,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "plugin failed")[:500])
    text = (proc.stdout or "").strip()
    if not text:
        return {"ok": True, "result": None}
    try:
        return {"ok": True, "result": json.loads(text)}
    except json.JSONDecodeError:
        return {"ok": True, "result": text[:4000]}
