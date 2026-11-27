"""One tool registry shared by the main AGI and sub AGIs.

A tool is defined once.  Profiles decide which tools a role may see and call;
there are no duplicate main/sub implementations.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

Handler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    id: str
    handler: Handler
    risk: str
    profiles: frozenset[str]
    description: str = ""
    timeout: int = 10


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.id in self._tools:
            raise ValueError(f"duplicate tool: {spec.id}")
        self._tools[spec.id] = spec

    def get(self, tool_id: str) -> ToolSpec:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {tool_id}") from exc

    def for_profile(self, profile: str) -> list[ToolSpec]:
        return [t for t in self._tools.values() if profile in t.profiles]

    def invoke(self, profile: str, tool_id: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        spec = self.get(tool_id)
        if profile not in spec.profiles:
            raise PermissionError(f"tool {tool_id} is not allowed for profile {profile}")
        return spec.handler(args or {})


def _http_json(url: str, timeout: int = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status, "data": json.loads(resp.read().decode("utf-8") or "{}")}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        return {"ok": False, "status": exc.code, "error": body}
    except Exception as exc:  # noqa: BLE001 - returned as a tool result
        return {"ok": False, "status": 0, "error": f"{type(exc).__name__}: {exc}"}


def health(args: dict[str, Any]) -> dict[str, Any]:
    base = str(args.get("base_url") or "http://127.0.0.1:8001").rstrip("/")
    result = _http_json(base + "/health", int(args.get("timeout") or 10))
    result["base_url"] = base
    return result


def version(args: dict[str, Any]) -> dict[str, Any]:
    base = str(args.get("base_url") or "http://127.0.0.1:8001").rstrip("/")
    result = _http_json(base + "/version", int(args.get("timeout") or 10))
    result["base_url"] = base
    return result


def task_list(args: dict[str, Any]) -> dict[str, Any]:
    base = str(args.get("base_url") or "http://127.0.0.1:8001").rstrip("/")
    token = str(args.get("token") or "")
    req = urllib.request.Request(base + "/hq/tasks", headers={"Accept": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, "status": resp.status, "data": json.loads(resp.read().decode("utf-8") or "{}")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "error": str(exc)}


def _api(method: str, args: dict[str, Any], path: str, body: dict | None = None,
         extra_headers: dict[str, str] | None = None) -> dict[str, Any]:
    base = str(args.get("base_url") or "http://127.0.0.1:8001").rstrip("/")
    token = str(args.get("token") or "")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if extra_headers:
        headers.update(extra_headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"ok": True, "status": resp.status, "data": json.loads(resp.read().decode("utf-8") or "{}")}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": exc.read().decode("utf-8", "replace")[:500]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "error": f"{type(exc).__name__}: {exc}"}


def task_create(args: dict[str, Any]) -> dict[str, Any]:
    payload = args.get("payload") or {}
    return _api("POST", args, "/hq/campaigns", payload if isinstance(payload, dict) else {})


def task_claim(args: dict[str, Any]) -> dict[str, Any]:
    platform = str(args.get("platform") or "reddit")
    manual = "true" if args.get("manual", True) else "false"
    headers = {"X-SASES-Executor": str(args.get("executor") or "main-agi")}
    return _api("POST", args, f"/hq/tasks/claim?platform={platform}&manual={manual}", {}, headers)


def task_receipt(args: dict[str, Any]) -> dict[str, Any]:
    task_id = int(args.get("task_id") or 0)
    body = {
        "status": str(args.get("status") or "done"),
        "result": args.get("result") or {},
        "error": args.get("error") or "",
    }
    return _api("POST", args, f"/hq/tasks/{task_id}/receipt", body)


def _verify_candidate(args: dict[str, Any]) -> dict[str, Any]:
    from .staging import verify
    root = str(args.get("root") or "")
    if not root:
        return {"ok": False, "error": "root is required"}
    return verify(root, int(args.get("port") or 8030))


def _browser(args: dict[str, Any], action: str) -> dict[str, Any]:
    from . import browser
    return getattr(browser, action)(args)


def build_default_registry() -> ToolRegistry:
    from .deploy import plan_promote, plan_rollback, plan_stage

    registry = ToolRegistry()
    registry.register(ToolSpec("node.health", health, "read", frozenset({"main", "sub"}),
                               "Read /health from a SASES node"))
    registry.register(ToolSpec("node.version", version, "read", frozenset({"main", "sub"}),
                               "Read /version from a SASES node"))
    registry.register(ToolSpec("task.list", task_list, "read", frozenset({"main", "sub"}),
                               "List HQ tasks with an executor token"))
    registry.register(ToolSpec("task.create", task_create, "write", frozenset({"main"}),
                               "Create an HQ campaign (admin token)"))
    registry.register(ToolSpec("task.claim", task_claim, "write", frozenset({"main", "sub"}),
                               "Claim one manual HQ task"))
    registry.register(ToolSpec("task.receipt", task_receipt, "write", frozenset({"main", "sub"}),
                               "Submit a task receipt"))
    registry.register(ToolSpec("browser.open", lambda a: _browser(a, "open_page"), "read",
                               frozenset({"main"}), "Open a URL in the CDP browser"))
    registry.register(ToolSpec("browser.fill", lambda a: _browser(a, "fill_page"), "write",
                               frozenset({"main"}), "Fill selectors and optionally click"))
    registry.register(ToolSpec("browser.click", lambda a: _browser(a, "click_page"), "write",
                               frozenset({"main"}), "Click a selector and screenshot"))
    registry.register(ToolSpec("deploy.stage", lambda a: plan_stage(
        str(a.get("node_id") or "local"), str(a.get("version") or "next"), int(a.get("port") or 8002)),
        "deploy", frozenset({"main"}), "Plan a staging deploy (dry run)"))
    registry.register(ToolSpec("deploy.verify", lambda a: _verify_candidate(a),
        "deploy", frozenset({"main"}), "Run a candidate package on an alternate port"))
    registry.register(ToolSpec("deploy.promote", lambda a: plan_promote(
        str(a.get("node_id") or "local"), str(a.get("version") or "next")),
        "deploy", frozenset({"main"}), "Plan a promote (approval required)"))
    registry.register(ToolSpec("deploy.rollback", lambda a: plan_rollback(
        str(a.get("node_id") or "local"), str(a.get("version") or "previous")),
        "deploy", frozenset({"main"}), "Plan a rollback (approval required)"))
    return registry
