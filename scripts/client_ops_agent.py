#!/usr/bin/env python3
"""SASES remote operations agent.

Runs on the client, polls the server for allowlisted operations, executes them
locally and posts the result.  It never accepts arbitrary shell commands.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BASE_URL = os.environ.get("SASES_BASE_URL", "http://120.77.136.90:8001").rstrip("/")
IDENTITY = os.path.join(ROOT, "node_identity.json")


def _identity() -> dict:
    with open(IDENTITY, encoding="utf-8") as handle:
        return json.load(handle)


def _headers(identity: dict) -> dict:
    return {
        "X-SASES-Node-Manifest": identity.get("manifest", ""),
        "Content-Type": "application/json",
    }


def _version() -> dict:
    try:
        return httpx.get(BASE_URL + "/version", timeout=5).json()
    except Exception as exc:
        return {"error": str(exc)}


def _runtime_port() -> int | None:
    path = os.path.join(ROOT, "runtime_port.json")
    if not os.path.exists(path):
        return None
    try:
        return int(json.load(open(path, encoding="utf-8")).get("port"))
    except Exception:
        return None


def _execute(action: str, payload: dict) -> dict:
    if action == "status":
        version = _version()
        client_version = {}
        try:
            client_version = json.load(open(os.path.join(ROOT, "client_version.json"), encoding="utf-8"))
        except Exception:
            pass
        return {"version": version, "client_version": client_version, "port": _runtime_port()}

    if action == "update_client":
        from scripts.client_updater import check_and_apply
        return check_and_apply(ROOT)

    if action == "start_client":
        if _version().get("schema_version"):
            return {"already_running": True, "version": _version()}
        subprocess.Popen(
            [sys.executable, os.path.join(ROOT, "scripts", "run_forever.py")],
            cwd=ROOT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        time.sleep(6)
        return {"started": True, "version": _version(), "port": _runtime_port()}

    if action == "stop_client":
        port = _runtime_port()
        path = os.path.join(ROOT, "runtime_port.json")
        pid = None
        if os.path.exists(path):
            try:
                pid = int(json.load(open(path, encoding="utf-8")).get("pid"))
            except Exception:
                pid = None
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
        return {"stopped": True, "pid": pid, "port": port}

    if action in ("install_wireguard", "import_tunnel"):
        from launcher.wireguard_setup import ensure_wireguard
        config = payload.get("config_path") if action == "import_tunnel" else None
        return ensure_wireguard(ROOT, config)

    if action == "capture_screen":
        from core.harness_loader import load_harness_modules
        modules = load_harness_modules(os.path.join(ROOT, "harness_modules"))
        params = dict(payload or {})
        params.setdefault("save_path", os.path.join(ROOT, "data", "screenshots", "remote.png"))
        params.setdefault("return_base64", True)
        return modules["screen_capture"]["run_fn"](params)

    return {"error": f"unsupported action: {action}"}


def main() -> int:
    once = os.environ.get("SASES_OPS_AGENT_ONCE", "").lower() in ("1", "true", "yes")
    while True:
        try:
            identity = _identity()
            response = httpx.post(
                BASE_URL + "/client/ops/claim",
                headers=_headers(identity),
                json={"node_id": identity.get("node_id")},
                timeout=10,
            )
            response.raise_for_status()
            operation = response.json().get("operation")
            if operation:
                try:
                    result = _execute(operation["action"], operation.get("payload") or {})
                    status = "done"
                except Exception as exc:
                    result = {"error": str(exc)}
                    status = "failed"
                httpx.post(
                    BASE_URL + "/client/ops/result",
                    headers=_headers(identity),
                    json={"id": operation["id"], "status": status, "result": result},
                    timeout=20,
                ).raise_for_status()
                print(f"[ops] {operation['id']} {operation['action']} -> {status}", flush=True)
        except Exception as exc:
            print(f"[ops] poll failed: {exc}", flush=True)
        if once:
            return 0
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
