"""Local Agent Runtime: a bounded scheduler for local subagents.

One process, multiple sessions, a single browser lock, heartbeat and approval
gating. This replaces running several local_worker processes at once.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path

from . import browser, browser_agent, browser_lease, browser_process, browser_profiles, browser_snapshot, browser_tab, capacity, disk_guard, fallback_policy, local_outbox, local_store, page_state
from .local_worker import _call, _execute, _read_only
from .tools import build_default_registry


class LocalRuntime:
    def __init__(self, server: str, token: str, max_workers: int = 0, lock_port: int = 8765) -> None:
        self.server = server
        self.token = token
        self.registry = build_default_registry()
        self.capacity = capacity.detect()
        override = max_workers or int(os.environ.get("SASES_LOCAL_WORKERS", "0") or 0)
        self.workers = max(2, override or int(self.capacity["workers"]))
        self.pool = ThreadPoolExecutor(max_workers=self.workers)
        self.browser_workers = max(1, len(browser_profiles.mapping()))
        self.browser_pool = ThreadPoolExecutor(max_workers=self.browser_workers)
        self.browser_active = 0
        self.general_active = 0
        try:
            local_store.set_metric("capacity_browser_workers", float(self.browser_workers))
        except Exception:
            pass
        for key in ("workers", "cpu", "memory_gb"):
            try:
                local_store.set_metric("capacity_" + key, float(self.capacity.get(key, self.workers)))
            except Exception:
                pass
        self.active: set[str] = set()
        self.lock = threading.Lock()
        self.browser_leases = browser_lease.BrowserLeases()
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

    def _agent_is_browser(self, agent: dict, steps: list[dict] | None = None) -> bool:
        if steps is None:
            try:
                steps = (json.loads(agent.get("task_json") or "{}").get("steps") or [])
            except json.JSONDecodeError:
                steps = []
        return self._is_browser(steps)

    def _submit(self, agent: dict, approved: bool = False, approval_id: int = 0,
                steps: list[dict] | None = None) -> None:
        if self._agent_is_browser(agent, steps):
            self.browser_pool.submit(self._run, agent, approved, approval_id)
        else:
            self.pool.submit(self._run, agent, approved, approval_id)

    def _platform_fallback(self, agent: dict, task: dict, steps: list[dict],
                           err: str, inner: dict, goal: str) -> dict:
        if (not inner.get("fallback_agent_id") and self._is_browser(steps)
                and "platform_limit" in err.lower()
                and fallback_policy.platform_enabled()
                and int(task.get("fallback_depth") or 0) < 1):
            adapter_step = next((s for s in steps if s.get("tool") == "adapter.run"), None)
            if adapter_step:
                old_args = dict(adapter_step.get("args") or {})
                current_platform = str(old_args.get("adapter") or "").lower()
                adapter_args = old_args.get("args") if isinstance(old_args.get("args"), dict) else old_args
                media = "video" if adapter_args.get("video") else ("image" if adapter_args.get("image") else "")
                alt_platform = fallback_policy.choose_platform(current_platform, media)
                if alt_platform:
                    next_task = dict(task)
                    next_task["fallback_depth"] = 1
                    new_steps = []
                    for step in steps:
                        if step is adapter_step:
                            copied = dict(step)
                            copied_args = dict(old_args)
                            copied_args["adapter"] = alt_platform
                            copied["args"] = copied_args
                            new_steps.append(copied)
                        else:
                            new_steps.append(step)
                    next_task["steps"] = new_steps
                    try:
                        spawned = _call(self.server, self.token, "POST", "/agents/spawn", {
                            "node_id": "local",
                            "name": (str(agent.get("name") or "browser task") + " (" + alt_platform + " fallback)")[:80],
                            "goal": goal,
                            "status": "queued",
                            "ttl": 300,
                            "parent_agent_id": str(agent.get("agent_id") or ""),
                            "task": next_task,
                            "context": {"conversation_id": (
                                json.loads(agent.get("context_json") or "{}").get("conversation_id")
                                if agent.get("context_json") else None)},
                        })
                        if spawned.get("agent_id"):
                            inner["fallback_agent_id"] = spawned["agent_id"]
                            inner["fallback_platform"] = alt_platform
                    except Exception:
                        pass
        return inner

    def _run(self, agent: dict, approved: bool = False, approval_id: int = 0) -> None:
        agent_id = str(agent.get("agent_id") or "")
        task = self._json(agent)
        goal = str(agent.get("goal") or task.get("goal") or "local task")
        steps = task.get("steps") if isinstance(task.get("steps"), list) else []
        page_name = ""
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
                local_store.finish(agent_id, "quota_blocked")
                return
            safe, reason = (True, "") if approved else _read_only(self.registry, steps)
            if not safe:
                approval = _call(self.server, self.token, "POST", "/approvals", {
                    "tool": "agent.execute",
                    "args": {"agent_id": agent_id, "steps": steps,
                             "attempt": local_store.attempts(agent_id)},
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
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                      {"status": "done", "result": {"ok": True, "skipped": True}})
                return

            def on_step(index: int, step: dict, result: dict) -> None:
                local_store.step(agent_id, current + index + 1)
                try:
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/trace", {
                        "seq": current + index + 1,
                        "event_type": "step",
                        "tool": str(step.get("tool") or ""),
                        "args": step.get("args") or {},
                        "result": result,
                    })
                except Exception:
                    pass

            deadline = time.monotonic() + float(os.environ.get("SASES_TASK_TIMEOUT", "900"))
            cancel_state = {"timed_out": False, "cancelled": False}

            def should_continue() -> bool:
                if time.monotonic() > deadline:
                    cancel_state["timed_out"] = True
                    return False
                try:
                    status = _call(self.server, self.token, "GET",
                                   f"/agents/{agent_id}").get("agent", {}).get("status", "")
                    if status == "cancelled":
                        cancel_state["cancelled"] = True
                        return False
                except Exception:
                    pass
                return True

            def capture_failure(outcome: dict) -> dict:
                inner = dict(outcome.get("result") or {})
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
                        inner["snapshot"] = snap_data
                        inner["recovery"] = browser_agent.plan(snap_data, goal, profile, list(browser_profiles.mapping()))
                        if ps["state"] == "upload_limit":
                            inner["error"] = "platform_limit: " + (ps["reason"] or "upload limit")
                        outcome["snapshot"] = snap_data
                        outcome["recovery"] = inner["recovery"]
                except Exception:
                    pass
                return inner

            if self._is_browser(steps):
                wait_started = time.perf_counter()
                profile = browser_lease.BrowserLeases.profile_for(task)
                platforms = sorted({
                    str((s.get("args") or {}).get("adapter") or "").lower()
                    for s in steps if s.get("tool") == "adapter.run"
                } - {""})
                with ExitStack() as stack:
                    for platform in platforms:
                        stack.enter_context(self.browser_leases.acquire("platform:" + platform))
                    stack.enter_context(self.browser_leases.acquire(profile))
                    browser.set_cdp(browser_profiles.cdp_for(profile))
                    page_name = agent_id
                    try:
                        browser_tab.new_tab(page_name)
                    except Exception:
                        pass
                    _old_page_name = os.environ.get("SASES_BROWSER_PAGE_NAME")
                    os.environ["SASES_BROWSER_PAGE_NAME"] = page_name
                    waited_ms = (time.perf_counter() - wait_started) * 1000
                    exec_started = time.perf_counter()
                    stop_watch = threading.Event()

                    def watch_task() -> None:
                        while not stop_watch.wait(1):
                            if time.monotonic() > deadline:
                                cancel_state["timed_out"] = True
                                browser_process.kill(agent_id)
                                return
                            try:
                                status = _call(self.server, self.token, "GET",
                                               f"/agents/{agent_id}").get("agent", {}).get("status", "")
                                if status == "cancelled":
                                    cancel_state["cancelled"] = True
                                    browser_process.kill(agent_id)
                                    return
                            except Exception:
                                pass

                    watcher = threading.Thread(target=watch_task, daemon=True)
                    watcher.start()
                    try:
                        outcome = _execute(self.server, self.token, self.registry, agent_id, remaining,
                                           goal, on_step=on_step, defer_finish=True,
                                           should_continue=should_continue)
                    finally:
                        stop_watch.set()
                        watcher.join(timeout=1)
                    local_store.set_metric("last_browser_wait_ms", waited_ms)
                    local_store.set_metric("last_browser_exec_ms",
                                           (time.perf_counter() - exec_started) * 1000)
                    inner = dict(outcome.get("result") or {})
                    if not outcome.get("ok"):
                        inner = capture_failure(outcome)
                    try:
                        browser_tab.close_tab(page_name)
                    except Exception:
                        pass
                    if _old_page_name is None:
                        os.environ.pop("SASES_BROWSER_PAGE_NAME", None)
                    else:
                        os.environ["SASES_BROWSER_PAGE_NAME"] = _old_page_name
                    browser.set_cdp("")
            else:
                outcome = _execute(self.server, self.token, self.registry, agent_id, remaining,
                                   goal, on_step=on_step, defer_finish=True,
                                   should_continue=should_continue)
                inner = dict(outcome.get("result") or {})

            if cancel_state["timed_out"] or cancel_state["cancelled"]:
                if cancel_state["cancelled"]:
                    local_store.finish(agent_id, "cancelled")
                else:
                    local_store.finish(agent_id, "failed")
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                          {"status": "failed", "result": {"ok": False, "error": "task_timeout"}})
                return
            if outcome.get("cancelled"):
                if cancel_state["cancelled"]:
                    local_store.finish(agent_id, "cancelled")
                else:
                    local_store.finish(agent_id, "failed")
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                          {"status": "failed", "result": {"ok": False, "error": "task_timeout"}})
                return
            if outcome.get("ok"):
                local_store.clear_attempts(agent_id)
                local_store.finish(agent_id, "done")
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                      {"status": "done", "result": inner or {"ok": True}})
                if approval_id:
                    try:
                        _call(self.server, self.token, "POST", "/approvals/executed", {"id": approval_id})
                    except Exception:
                        pass
                return

            err = str(inner.get("error") or outcome.get("error") or "")
            retryable = not any(k in err.lower() for k in (
                "platform_limit", "login", "captcha", "disk_full", "quota", "approval"))
            attempts = local_store.note_attempt(agent_id) if retryable else 0
            if retryable and attempts <= 1:
                try:
                    if self._is_browser(steps):
                        local_store.rewind(agent_id)
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/requeue")
                    _call(self.server, self.token, "POST", f"/agents/{agent_id}/progress",
                          {"progress": f"重试 {attempts + 1}/2"})
                    return
                except Exception:
                    pass
            if (self._is_browser(steps) and "login_required" in err.lower()
                    and fallback_policy.enabled() and int(task.get("fallback_depth") or 0) < 1):
                current_profile = str(task.get("browser_profile") or "default")
                alt = fallback_policy.choose_profile(current_profile, list(browser_profiles.mapping()))
                if alt:
                    next_task = dict(task)
                    next_task["browser_profile"] = alt
                    next_task["fallback_depth"] = 1
                    try:
                        spawned = _call(self.server, self.token, "POST", "/agents/spawn", {
                            "node_id": "local",
                            "name": (str(agent.get("name") or "browser task") + " (fallback)")[:80],
                            "goal": goal,
                            "status": "queued",
                            "ttl": 300,
                            "parent_agent_id": agent_id,
                            "task": next_task,
                            "context": {"conversation_id": (
                                json.loads(agent.get("context_json") or "{}").get("conversation_id")
                                if agent.get("context_json") else None)},
                        })
                        if spawned.get("agent_id"):
                            inner["fallback_agent_id"] = spawned["agent_id"]
                            inner["fallback_profile"] = alt
                    except Exception:
                        pass
            inner = self._platform_fallback(agent, task, steps, err, inner, goal)
            local_store.finish(agent_id, "failed")
            _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish",
                  {"status": "failed", "result": inner or {"ok": False, "error": err}})
            try:
                _call(self.server, self.token, "POST", "/escalations", {
                    "node_id": str(agent.get("node_id") or "local"),
                    "reason": "子智能体执行失败: " + (err or "unknown"),
                    "severity": "critical" if "platform_limit" in err else "high",
                    "conversation_id": (json.loads(agent.get("context_json") or "{}").get("conversation_id")
                                        if agent.get("context_json") else None),
                    "evidence": {"agent_id": agent_id, "result": inner},
                })
            except Exception:
                pass
            if approval_id:
                try:
                    _call(self.server, self.token, "POST", "/approvals/executed", {"id": approval_id})
                except Exception:
                    pass
        except Exception as exc:  # noqa: BLE001
            try:
                _call(self.server, self.token, "POST", f"/agents/{agent_id}/finish", {
                    "status": "failed", "result": {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                })
            except Exception:
                pass
        finally:
            if page_name:
                try:
                    browser_tab.close_tab(page_name)
                except Exception:
                    pass
            with self.lock:
                self.active.discard(agent_id)
                if self._agent_is_browser(agent, steps):
                    self.browser_active = max(0, self.browser_active - 1)
                else:
                    self.general_active = max(0, self.general_active - 1)

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
            browser = self._agent_is_browser(agent, steps)
            with self.lock:
                if browser:
                    if self.browser_active >= self.browser_workers:
                        continue
                    self.browser_active += 1
                else:
                    if self.general_active >= self.workers:
                        continue
                    self.general_active += 1
                self.active.add(agent_id)
            _call(self.server, self.token, "POST", "/approvals/executed", {"id": int(row["id"])})
            self._submit(agent, True, int(row["id"]), steps)
            return {"ok": True, "started": agent_id, "approved": True}

        listing = _call(self.server, self.token, "GET", "/agents")
        for agent in listing.get("agents", []):
            agent_id = str(agent.get("agent_id") or "")
            if agent.get("status") != "queued" or str(agent.get("node_id") or "") not in ("local", "desktop"):
                continue
            browser = self._agent_is_browser(agent)
            with self.lock:
                if agent_id in self.active:
                    continue
                if browser:
                    if self.browser_active >= self.browser_workers:
                        continue
                    self.browser_active += 1
                else:
                    if self.general_active >= self.workers:
                        continue
                    self.general_active += 1
                self.active.add(agent_id)
            if not _call(self.server, self.token, "POST", f"/agents/{agent_id}/claim",
                         {"owner": "local-runtime", "ttl": 300}).get("ok"):
                with self.lock:
                    self.active.discard(agent_id)
                    if browser:
                        self.browser_active = max(0, self.browser_active - 1)
                    else:
                        self.general_active = max(0, self.general_active - 1)
                continue
            self._submit(agent)
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
    parser.add_argument("--max-workers", type=int, default=0)
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
