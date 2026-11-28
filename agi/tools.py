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
    input_schema: dict[str, Any] | None = None
    approval_required: bool = False
    idempotent: bool = False


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
        data = dict(args or {})
        if spec.input_schema:
            _validate_object(data, spec.input_schema)
        if spec.approval_required and not data.pop("_approved", False):
            return {"ok": False, "error": "approval_required", "tool": tool_id,
                    "risk": spec.risk}
        return spec.handler(data)


def _type_ok(value: Any, expected: str) -> bool:
    return {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }.get(expected, True)


def _validate_object(data: dict[str, Any], schema: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        return
    required = schema.get("required") or []
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"missing required arguments: {', '.join(missing)}")
    properties = schema.get("properties") or {}
    for key, rule in properties.items():
        if key in data and rule.get("type") and not _type_ok(data[key], rule["type"]):
            raise ValueError(f"{key} must be {rule['type']}")


def _http_json(url: str, timeout: int = 10) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
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


def _recovery_plan(args: dict[str, Any]) -> dict[str, Any]:
    from .recovery import plan_failure
    return plan_failure(
        str(args.get("node_id") or "local"),
        int(args.get("task_id") or 0),
        int(args.get("attempts") or 0),
        str(args.get("reason") or ""),
    )


def _platform_check(args: dict[str, Any]) -> dict[str, Any]:
    from .platform_policy import check
    return check(str(args.get("url") or ""), str(args.get("action") or "open_for_human"),
                 bool(args.get("manual_approved")))


def _skill(args: dict[str, Any], action: str) -> dict[str, Any]:
    from . import skills
    if action == "list":
        return {"skills": skills.list_skills()}
    if action == "load":
        return skills.load_skill(str(args.get("name") or ""))
    if action == "evaluate":
        return skills.evaluate_skill(str(args.get("name") or ""))
    raise ValueError(f"unknown skill action: {action}")


def _mcp(args: dict[str, Any], action: str) -> dict[str, Any]:
    from . import mcp_bridge
    if action == "servers":
        return mcp_bridge.list_servers()
    if action == "tools":
        return mcp_bridge.list_tools(int(args.get("server_id") or 0))
    if action == "call":
        return mcp_bridge.call(int(args.get("server_id") or 0), str(args.get("tool") or ""),
                               args.get("arguments") or {})
    raise ValueError(f"unknown mcp action: {action}")


def _planner(args: dict[str, Any], registry: "ToolRegistry") -> dict[str, Any]:
    from .planner import plan
    return plan(str(args.get("goal") or ""), registry,
                str(args.get("base_url") or "http://127.0.0.1:8001"),
                int(args.get("max_steps") or 5))


def _plugin(args: dict[str, Any], action: str) -> dict[str, Any]:
    from . import plugin_bridge
    if action == "list":
        return plugin_bridge.list_plugins()
    if action == "run":
        return plugin_bridge.run_tool(str(args.get("plugin_id") or ""),
                                      args.get("params") or {})
    raise ValueError(f"unknown plugin action: {action}")


def _adapter(args: dict[str, Any], action: str) -> dict[str, Any]:
    from . import adapters
    if action == "list":
        return {"adapters": adapters.list_adapters()}
    if action == "run":
        return adapters.run(str(args.get("adapter") or ""), args.get("args") or {})
    raise ValueError(f"unknown adapter action: {action}")


def _support(args: dict[str, Any], action: str) -> dict[str, Any]:
    from . import support
    import sqlite3
    if action == "classify":
        return support.classify(str(args.get("query") or ""))
    if action == "search":
        return {"results": support.search(str(args.get("query") or ""), int(args.get("limit") or 3))}
    if action == "draft":
        return support.draft_reply(str(args.get("query") or ""))
    if action == "ticket":
        conn = sqlite3.connect(str(args.get("db") or "data/agi.db"))
        try:
            return support.create_ticket(conn, str(args.get("need") or ""),
                                         str(args.get("customer") or ""),
                                         str(args.get("source") or "chat"),
                                         str(args.get("platform") or ""),
                                         str(args.get("evidence") or ""))
        finally:
            conn.close()
    raise ValueError(f"unknown support action: {action}")


def build_default_registry() -> ToolRegistry:
    from .deploy import plan_promote, plan_rollback, plan_stage
    from . import capabilities, fs_tools, image_tools, local_bridge, ocr_tools, office_tools, pdf_tools, shell_tools, subagent_tools, web_tools

    registry = ToolRegistry()
    for tool_id, handler, description in (
        ("fs.list", fs_tools.list_dir, "List files under the configured workspace"),
        ("fs.read", fs_tools.read_file, "Read a text file under the configured workspace"),
        ("fs.grep", fs_tools.grep, "Search text under the configured workspace"),
        ("fs.glob", fs_tools.glob_files, "Find files under the configured workspace"),
        ("web.fetch", web_tools.fetch, "Fetch a public HTTP(S) page"),
        ("web.search", web_tools.search, "Search the public web"),
        ("office.read", office_tools.read, "Extract text from docx/xlsx/pptx"),
        ("pdf.read", pdf_tools.read, "Extract text from PDF"),
        ("image.read", image_tools.read, "Read image metadata"),
        ("ocr.image", ocr_tools.image, "Extract text from an image via vision model"),
    ):
        registry.register(ToolSpec(tool_id, handler, "read", frozenset({"main", "sub"}), description))
    for tool_id, handler, description in (
        ("fs.write", fs_tools.write_file, "Write a workspace file (approval required)"),
        ("fs.edit", fs_tools.edit_file, "Edit a workspace file (approval required)"),
        ("fs.mkdir", fs_tools.mkdir, "Create a workspace directory (approval required)"),
        ("fs.copy", fs_tools.copy_path, "Copy a workspace path (approval required)"),
        ("fs.move", fs_tools.move_path, "Move a workspace path (approval required)"),
        ("fs.delete", fs_tools.delete_path, "Delete a workspace path (approval required)"),
        ("shell.write", shell_tools.run_write, "Allowlisted mkdir/copy/move (approval required)"),
        ("office.write", office_tools.write, "Write docx/xlsx/pptx (approval required)"),
    ):
        registry.register(ToolSpec(tool_id, handler, "write", frozenset({"main", "sub"}), description))
    registry.register(ToolSpec("shell.run", shell_tools.run, "read", frozenset({"main", "sub"}),
                               "Run a read-only allowlisted shell command"))
    for tool_id, local_tool in (
        ("local.fs.list", "fs.list"),
        ("local.fs.read", "fs.read"),
        ("local.fs.grep", "fs.grep"),
        ("local.fs.glob", "fs.glob"),
        ("local.shell.run", "shell.run"),
        ("local.office.read", "office.read"),
        ("local.pdf.read", "pdf.read"),
        ("local.image.read", "image.read"),
        ("local.ocr.image", "ocr.image"),
    ):
        registry.register(ToolSpec(tool_id, lambda a, t=local_tool: local_bridge.run_readonly(t, a),
                                   "read", frozenset({"main"}),
                                   "Read-only local runtime " + local_tool))
    for tool_id, local_tool in (
        ("local.fs.write", "fs.write"),
        ("local.fs.edit", "fs.edit"),
        ("local.fs.mkdir", "fs.mkdir"),
        ("local.fs.copy", "fs.copy"),
        ("local.fs.move", "fs.move"),
        ("local.fs.delete", "fs.delete"),
        ("local.shell.write", "shell.write"),
    ):
        registry.register(ToolSpec(tool_id, lambda a, t=local_tool: local_bridge.start(t, a),
                                   "write", frozenset({"main"}),
                                   "Queue a local write; local runtime requires approval"))
    registry.register(ToolSpec("node.health", health, "read", frozenset({"main", "sub"}),
                               "Read /health from a SASES node"))
    def workflow_run(args: dict) -> dict:
        steps = args.get("steps")
        if not isinstance(steps, list) or not steps:
            return {"ok": False, "error": "steps is required"}
        results = []
        for step in steps[:10]:
            tool = str((step or {}).get("tool") or "")
            if tool == "workflow.run":
                return {"ok": False, "error": "recursive workflow is not allowed"}
            try:
                spec = registry.get(tool) if tool else None
            except KeyError:
                spec = None
            if not spec or spec.risk != "read":
                return {"ok": False, "error": f"workflow only allows read tools: {tool}"}
            cargs = step.get("args") if isinstance(step.get("args"), dict) else {}
            try:
                result = registry.invoke("main", tool, cargs)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            results.append({"tool": tool, "result": result})
            if not result.get("ok"):
                break
        return {"ok": all(r["result"].get("ok") for r in results), "results": results}

    registry.register(ToolSpec("workflow.run", workflow_run, "read", frozenset({"main"}),
                               "Run a bounded read-only tool workflow"))
    for tool_id, handler, risk, desc in (
        ("subagent.spawn", subagent_tools.spawn, "write", "Spawn a child agent with explicit steps"),
        ("subagent.wait", subagent_tools.wait, "read", "Wait for a child agent"),
        ("subagent.message", subagent_tools.message, "write", "Send a steering message to a child agent"),
        ("subagent.cancel", subagent_tools.cancel, "write", "Cancel a child agent"),
        ("subagent.trace", subagent_tools.trace, "read", "Read a child agent trace"),
    ):
        registry.register(ToolSpec(tool_id, handler, risk, frozenset({"main"}), desc))
    registry.register(ToolSpec("capability.list", lambda a: capabilities.list_manifest(registry),
                               "read", frozenset({"main", "sub"}),
                               "List tool profiles and role-policy audit"))
    registry.register(ToolSpec("agent.trace", lambda a: _api(
        "GET", a, "/agents/" + str(a.get("agent_id") or "") + "/trace"), "read",
        frozenset({"main", "sub"}), "Read a child agent tool trace"))
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
    registry.register(ToolSpec("browser.snapshot", lambda a: _browser(a, "snapshot"), "read",
                               frozenset({"main", "sub"}), "Read the current browser page snapshot"))
    registry.register(ToolSpec("browser.fill", lambda a: _browser(a, "fill_page"), "write",
                               frozenset({"main"}), "Fill selectors and optionally click"))
    registry.register(ToolSpec("browser.wait_for", lambda a: _browser(a, "wait_for"), "read",
                               frozenset({"main", "sub"}), "Wait for a selector/role/text target"))
    registry.register(ToolSpec("browser.extract", lambda a: _browser(a, "extract"), "read",
                               frozenset({"main", "sub"}), "Extract text or value from a target"))
    registry.register(ToolSpec("browser.upload", lambda a: _browser(a, "upload"), "write",
                               frozenset({"main"}), "Set a file on an upload input"))
    registry.register(ToolSpec("browser.click_target", lambda a: _browser(a, "click_target"), "write",
                               frozenset({"main", "sub"}), "Click by selector/role/name/text with fallback"))
    registry.register(ToolSpec("browser.fill_targets", lambda a: _browser(a, "fill_targets"), "write",
                               frozenset({"main", "sub"}), "Fill fields by selector/role/label/text with fallback"))
    registry.register(ToolSpec("browser.click_element", lambda a: _browser(a, "click_element"), "write",
                               frozenset({"main"}), "Click the center of a snapshot element bbox"))
    registry.register(ToolSpec("browser.visual_click", lambda a: _browser(a, "visual_click"), "write",
                               frozenset({"main"}), "Locate a target with a vision model and click it"))
    registry.register(ToolSpec("browser.click_at", lambda a: _browser(a, "click_at"), "write",
                               frozenset({"main"}), "Click viewport coordinates from a screenshot"))
    registry.register(ToolSpec("browser.click", lambda a: _browser(a, "click_page"), "write",
                               frozenset({"main"}), "Click a selector and screenshot"))
    registry.register(ToolSpec("browser.reddit_post", lambda a: _browser(a, "reddit_post"), "write",
                               frozenset({"main"}), "Fill and optionally submit a Reddit post"))
    registry.register(ToolSpec("browser.douyin_post", lambda a: _browser(a, "douyin_post"), "write",
                               frozenset({"main"}), "Upload and optionally publish a Douyin image post"))
    registry.register(ToolSpec("browser.bilibili_post", lambda a: _browser(a, "bilibili_post"), "write",
                               frozenset({"main"}), "Upload and optionally publish a Bilibili video"))
    registry.register(ToolSpec("browser.youtube_post", lambda a: _browser(a, "youtube_post"), "write",
                               frozenset({"main"}), "Upload and optionally publish a YouTube video"))
    registry.register(ToolSpec("recovery.plan", lambda a: _recovery_plan(a), "read",
                               frozenset({"main"}), "Plan retry or reroute after a failure"))
    registry.register(ToolSpec("platform.policy", lambda a: _platform_check(a), "read",
                               frozenset({"main", "sub"}), "Check platform automation policy"))
    registry.register(ToolSpec("skill.list", lambda a: _skill(a, "list"), "read",
                               frozenset({"main", "sub"}), "List versioned skills"))
    registry.register(ToolSpec("skill.load", lambda a: _skill(a, "load"), "read",
                               frozenset({"main", "sub"}), "Load a skill"))
    registry.register(ToolSpec("skill.evaluate", lambda a: _skill(a, "evaluate"), "read",
                               frozenset({"main"}), "Static skill evaluation"))
    registry.register(ToolSpec("mcp.servers", lambda a: _mcp(a, "servers"), "read",
                               frozenset({"main"}), "List MCP servers (disabled by default)"))
    registry.register(ToolSpec("mcp.tools", lambda a: _mcp(a, "tools"), "read",
                               frozenset({"main"}), "List MCP tools (disabled by default)"))
    registry.register(ToolSpec("mcp.call", lambda a: _mcp(a, "call"), "write",
                               frozenset({"main"}), "Call an MCP tool (disabled by default)"))
    registry.register(ToolSpec("planner.plan", lambda a: _planner(a, registry), "read",
                               frozenset({"main"}), "Plan a read-only tool sequence"))
    registry.register(ToolSpec("plugin.list", lambda a: _plugin(a, "list"), "read",
                               frozenset({"main"}), "List plugins (disabled by default)"))
    registry.register(ToolSpec("plugin.run", lambda a: _plugin(a, "run"), "write",
                               frozenset({"main"}), "Run a tool plugin (disabled by default)"))
    registry.register(ToolSpec("adapter.list", lambda a: _adapter(a, "list"), "read",
                               frozenset({"main"}), "List platform adapters"))
    registry.register(ToolSpec("adapter.run", lambda a: _adapter(a, "run"), "write",
                               frozenset({"main"}), "Run one platform adapter"))
    registry.register(ToolSpec("support.classify", lambda a: _support(a, "classify"), "read",
                               frozenset({"main", "sub"}), "Classify a support request"))
    registry.register(ToolSpec("support.kb_search", lambda a: _support(a, "search"), "read",
                               frozenset({"main", "sub"}), "Search the support knowledge base"))
    registry.register(ToolSpec("support.draft", lambda a: _support(a, "draft"), "read",
                               frozenset({"main", "sub"}), "Draft an answer from the knowledge base"))
    registry.register(ToolSpec("support.ticket", lambda a: _support(a, "ticket"), "write",
                               frozenset({"main", "sub"}), "Create a support ticket"))
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
