"""Local Agent Runtime: a bounded scheduler for local subagents.

One process, multiple sessions, a single browser lock, heartbeat and approval
gating. This replaces running several local_worker processes at once.
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .local_worker import _call, _execute, _read_only
from .tools import build_default_registry


class LocalRuntime:
    def __init__(self, server: str, token: str, max_workers: int = 2, lock_port: int = 8765) -> None:
        self.server = server
        self.token = token
        self.registry = build_default_registry()
        self.pool = ThreadPoolExecutor(max_workers=max(1, max_workers))
        self.active: set[str] = set()
        self.lock = threading.Lock()
        self.browser_lock = threading.Lock()
        self._lock_socket = None
        if lock_port:
            self._lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self._lock_socket.bind(("127.0.0.1", lock_port))
                self._lock_socket.listen(1)
            except OSError as exc:
                raise RuntimeError("another local runtime is already running") from exc
        self.running = True

    def _json(self, agent: dict) -> dict:
        try:
            return json.loads(agent.get("task_json") or "{}")
        except json.JSONDecodeError:
            return {}

    def _is_browser(self, steps: list[dict]) -> bool:
        return any(str(s.get("tool") or "").startswith(("browser.", "adapter.")) for s in steps)

    def _run(self, agent: dict) -> None:
        agent_id = str(agent.get("agent_id") or "")
        task = self._json(agent)
        goal = str(agent.get("goal") or task.get("goal") or "local task")
        steps = task.get("steps") if isinstance(task.get("steps"), list) else []
        try:
            safe, reason = _read_only(self.registry, steps)
            if not safe:
                approval = _call(self.server, self.token, "POST", "/approvals", {
                    "tool": "agent.execute",
                    "args": {"agent_id": agent_id, "steps": steps},
                    "description": f"{goal}: {reason}",
                    "risk": "high",
                })
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/progress", {"progress": "等待审批"})
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish", {
                    "status": "needs_approval",
                    "result": {"ok": False, "approval_id": approval.get("approval_id"), "reason": reason},
                })
                return
            if self._is_browser(steps):
                with self.browser_lock:
                    _execute(self.server, self.token, self.registry, agent_id, steps, goal)
            else:
                _execute(self.server, self.token, self.registry, agent_id, steps, goal)
        except Exception as exc:  # noqa: BLE001
            try:
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish", {
                    "status": "failed", "result": {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                })
            except Exception:
                pass
        finally:
            with self.lock:
                self.active.discard(agent_id)

    def poll(self) -> dict:
        approved = _call(self.server, self.token, "GET", "/approvals/approved").get("approvals", [])
        for row in approved:
            if row.get("tool") != "agent.execute":
                continue
            try:
                payload = json.loads(row.get("args_json") or "{}")
            except json.JSONDecodeError:
                continue
            agent_id = str(payload.get("agent_id") or "")
            steps = payload.get("steps") or []
            if not agent_id or not steps or agent_id in self.active:
                continue
            agent = _call(self.server, self.token, "GET", f"/agents/{agent_id}").get("agent", {})
            if str(agent.get("node_id") or "") not in ("local", "desktop"):
                continue
            agent["task_json"] = json.dumps({"steps": steps})
            with self.lock:
                self.active.add(agent_id)
            self.pool.submit(self._run, agent)
            _call(self.server, self.token, "POST", "/approvals/executed", {"id": int(row["id"])})
            return {"ok": True, "started": agent_id, "approved": True}

        listing = _call(self.server, self.token, "GET", "/agents")
        for agent in listing.get("agents", []):
            agent_id = str(agent.get("agent_id") or "")
            if agent.get("status") != "queued" or str(agent.get("node_id") or "") not in ("local", "desktop"):
                continue
            with self.lock:
                if agent_id in self.active or len(self.active) >= self.pool._max_workers:
                    continue
                self.active.add(agent_id)
            if not _call(self.server, self.token, "POST", f"/agents/{agent_id}/claim",
                         {"owner": "local-runtime", "ttl": 300}).get("ok"):
                with self.lock:
                    self.active.discard(agent_id)
                continue
            self.pool.submit(self._run, agent)
            return {"ok": True, "started": agent_id, "approved": False}
        return {"ok": True, "started": None}

    def heartbeat(self, outcome: dict | None = None) -> None:
        _call(self.server, self.token, "POST", "/local-worker/status", {
            "owner": "local-runtime",
            "current_agent": (outcome or {}).get("started"),
            "claimed": bool((outcome or {}).get("started")),
        })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://10.0.0.3:8099")
    parser.add_argument("--token-file", default="data/agi.fleet.token")
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--interval", type=float, default=1.5)
    args = parser.parse_args()
    token = Path(args.token_file).read_text(encoding="utf-8").strip()
    try:
        rt = LocalRuntime(args.server, token, args.max_workers)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), flush=True)
        return 1
    while True:
        try:
            outcome = rt.poll()
            rt.heartbeat(outcome)
            print(json.dumps(outcome, ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), flush=True)
        time.sleep(max(0.5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
