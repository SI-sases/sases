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

from . import browser_agent, browser_snapshot, disk_guard, local_outbox, local_store, page_state
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

    def _quota_block(self, steps: list[dict]) -> str:
        for step in steps:
            if step.get("tool") != "adapter.run":
                continue
            adapter = str((step.get("args") or {}).get("adapter") or "").lower()
            if not adapter:
                continue
            try:
                rows = _call(self.server, self.token, "GET",
                             f"/platform/quota?platform={adapter}").get("quota", [])
            except Exception:
                return ""
            if rows:
                return f"{adapter} quota exhausted until {rows[0].get('exhausted_until')}: {rows[0].get('reason')}"
        return ""

    def _is_browser(self, steps: list[dict]) -> bool:
        return any(str(s.get("tool") or "").startswith(("browser.", "adapter.")) for s in steps)

    def _run(self, agent: dict, approved: bool = False, approval_id: int = 0) -> None:
        agent_id = str(agent.get("agent_id") or "")
        task = self._json(agent)
        goal = str(agent.get("goal") or task.get("goal") or "local task")
        steps = task.get("steps") if isinstance(task.get("steps"), list) else []
        try:
            if self._is_browser(steps):
                try:
                    disk_guard.ensure_free(1.0)
                except disk_guard.DiskFullError as exc:
                    result = {"ok": False, "error": f"disk_full: {exc}", "disk_full": True}
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/progress", {"progress": "磁盘空间不足"})
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                          {"status": "failed", "result": result})
                    local_store.finish(agent_id, "failed")
                    return
            blocked = self._quota_block(steps)
            if blocked:
                result = {"ok": False, "error": blocked, "quota_blocked": True}
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/progress", {"progress": "平台配额耗尽"})
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                      {"status": "quota_blocked", "result": result})
                _call(self.server, self.token, "POST", "/escalations", {
                    "node_id": str(agent.get("node_id") or "local"),
                    "reason": "平台配额已耗尽: " + blocked,
                    "severity": "critical",
                    "evidence": {"agent_id": agent_id, "result": result},
                })
                local_store.finish(agent_id, "failed")
                return
            safe, reason = (True, "") if approved else _read_only(self.registry, steps)
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
            current = local_store.start(agent_id, goal, steps)
            remaining = steps[current:]
            if not remaining:
                local_store.finish(agent_id, "done")
                return

            def on_step(index: int, step: dict, result: dict) -> None:
                local_store.step(agent_id, current + index + 1)

            if self._is_browser(steps):
                wait_started = time.perf_counter()
                with self.browser_lock:
                    waited_ms = (time.perf_counter() - wait_started) * 1000
                    exec_started = time.perf_counter()
                    outcome = _execute(self.server, self.token, self.registry, agent_id, remaining,
                                       goal, on_step=on_step)
                    local_store.set_metric("last_browser_wait_ms", waited_ms)
                    local_store.set_metric("last_browser_exec_ms",
                                           (time.perf_counter() - exec_started) * 1000)
            else:
                outcome = _execute(self.server, self.token, self.registry, agent_id, remaining,
                                   goal, on_step=on_step)
            if not outcome.get("ok") and self._is_browser(steps):
                try:
                    snap_path = f"data/browser_snapshots/{agent_id}.png"
                    snap = browser_snapshot.capture(snap_path)
                    if snap.get("ok"):
                        ps = page_state.classify(snap.get("text", ""), snap.get("url", ""), snap.get("title", ""))
                        snap_data = {
                            "state": ps["state"],
                            "reason": ps["reason"],
                            "url": snap.get("url", ""),
                            "title": snap.get("title", ""),
                            "text": str(snap.get("text", ""))[-2000:],
                            "screenshot": snap.get("screenshot", ""),
                            "elements": (snap.get("elements") or [])[:20],
                            "dialogs": (snap.get("dialogs") or [])[:5],
                        }
                        outcome["snapshot"] = snap_data
                        try:
                            outcome["recovery"] = browser_agent.plan(snap_data, goal)
                        except Exception:
                            outcome["recovery"] = {"mode": "observe", "actions": [], "automatic": False}
                        if outcome.get("results"):
                            outcome["results"][-1]["snapshot"] = snap_data
                        if ps["state"] == "upload_limit":
                            outcome["error"] = "platform_limit: " + (ps["reason"] or "upload limit")
                            if outcome.get("results"):
                                outcome["results"][-1]["result"]["error"] = outcome["error"]
                        try:
                            finish_result = dict(outcome.get("result") or {})
                            finish_result["ok"] = False
                            finish_result["error"] = outcome.get("error") or finish_result.get("error") or "browser failed"
                            finish_result["snapshot"] = snap_data
                            finish_result["recovery"] = outcome.get("recovery") or {}
                            _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                                  {"status": "failed", "result": finish_result})
                        except Exception:
                            pass
                except Exception:
                    pass
            local_store.finish(agent_id, "done" if outcome.get("ok") else "failed")
            if not outcome.get("ok"):
                try:
                    _call(self.server, self.token, "POST", "/escalations", {
                        "node_id": str(agent.get("node_id") or "local"),
                        "reason": "子智能体执行失败: " + str((outcome.get("result") or {}).get("error") or "unknown"),
                        "severity": "critical" if "platform_limit" in str((outcome.get("result") or {}).get("error") or "") else "high",
                        "conversation_id": (json.loads(agent.get("context_json") or "{}").get("conversation_id")
                                            if agent.get("context_json") else None),
                        "evidence": {"agent_id": agent_id, "result": outcome.get("result")},
                    })
                except Exception:
                    pass
            if approval_id:
                _call(self.server, self.token, "POST", "/approvals/executed", {"id": approval_id})
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

    def cleanup_checkpoints(self, keep: set[str] | None = None, max_age: int = 86400) -> list[str]:
        keep = keep or set()
        removed = []
        root = Path("data") / "checkpoints"
        if not root.is_dir():
            return removed
        now = time.time()
        for path in root.glob("*.json"):
            agent_id = path.stem
            stale = now - path.stat().st_mtime > max_age
            if stale or agent_id not in keep:
                try:
                    path.unlink()
                    removed.append(path.name)
                except Exception:
                    pass
        return removed

    def recover(self) -> list[str]:
        recovered = []
        try:
            listing = _call(self.server, self.token, "GET", "/agents")
        except Exception:
            return recovered
        for agent in listing.get("agents", []):
            if str(agent.get("node_id") or "") not in ("local", "desktop"):
                continue
            if agent.get("status") != "active":
                continue
            agent_id = str(agent.get("agent_id") or "")
            try:
                if _call(self.server, self.token, "POST", f"/agents/{agent_id}/requeue", {}).get("ok"):
                    recovered.append(agent_id)
            except Exception:
                pass
        return recovered

    def flush_outbox(self) -> None:
        for row in local_outbox.pending():
            try:
                _call(self.server, self.token, "POST", f"/agents/{row['agent_id']}/finish",
                      {"status": row["status"], "result": row["result"]})
                local_outbox.remove(int(row["id"]))
            except Exception:
                local_outbox.bump(int(row["id"]))

    def poll(self) -> dict:
        self.flush_outbox()
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
            self.pool.submit(self._run, agent, True, int(row["id"]))
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
            "metrics": local_store.metrics(),
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
    try:
        browser_snapshot.cleanup()
        disk_guard.ensure_free(1.0)
    except Exception:
        pass
    recovered = rt.recover()
    try:
        active = _call(rt.server, rt.token, "GET", "/agents").get("agents", [])
        keep = {a.get("agent_id") for a in active if a.get("status") in ("queued", "active", "needs_approval")}
        rt.cleanup_checkpoints(keep)
    except Exception:
        pass
    idle = 0
    while True:
        try:
            outcome = rt.poll()
            rt.heartbeat(outcome)
            if outcome.get("started"):
                idle = 0
                print(json.dumps(outcome, ensure_ascii=False), flush=True)
            else:
                idle += 1
                if idle % 20 == 0:
                    print(json.dumps({"ok": True, "idle": idle}, ensure_ascii=False), flush=True)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), flush=True)
        delay = args.interval * min(4.0, 1.0 + idle / 5.0)
        time.sleep(max(0.5, delay))


if __name__ == "__main__":
    raise SystemExit(main())
