"""Optional LLM planner for the main AGI.

If no model is configured, a deterministic fallback returns a safe read-only
plan.  The planner never executes tools; it only returns validated steps.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .package import TaskPackage


FALLBACK = {
    "status": [{"tool": "node.health", "args": {}}, {"tool": "node.version", "args": {}}],
    "support": [{"tool": "support.draft", "args": {}}],
    "policy": [{"tool": "platform.policy", "args": {}}],
    "readme": [{"tool": "fs.read", "args": {"path": "README.md"}}],
}


def _registry_tools(registry) -> list[dict]:
    return [{"id": t.id, "description": t.description, "risk": t.risk} for t in registry.for_profile("main")]


def _fallback(goal: str) -> dict:
    low = (goal or "").lower()
    key = "readme" if any(w in low for w in ("readme", "文件", "调查")) else (
        "status" if any(w in low for w in ("状态", "status", "检查", "health")) else (
        "support" if any(w in low for w in ("客服", "support", "工单")) else (
            "policy" if any(w in low for w in ("平台", "policy", "小红书")) else "status")))
    return {"ok": True, "mode": "fallback", "steps": FALLBACK[key]}


def plan(goal: str, registry, base_url: str = "http://127.0.0.1:8001",
         max_steps: int = 5) -> dict:
    goal = (goal or "").strip()
    if not goal:
        return {"ok": False, "error": "goal is required", "steps": []}
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key or api_key.startswith("sk-dummy"):
        result = _fallback(goal)
        result["steps"] = _normalize(result["steps"], goal, base_url, registry, max_steps)
        return result

    try:
        from openai import OpenAI
        from core.config import DEEPSEEK_BASE_URL, MODEL_NAME
        client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        prompt = (
            "You are the SASES main AGI planner. Return JSON only: "
            '{"steps":[{"tool":"tool.id","args":{}}]}. '
            "Use only the provided tools. Do not invent tools. Max steps: %d.\n"
            "Goal: %s\nTools: %s" % (max_steps, goal, json.dumps(_registry_tools(registry), ensure_ascii=False))
        )
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": "Return JSON only."},
                      {"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            timeout=20,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.strip("`").replace("json\n", "", 1).strip()
        data = json.loads(text)
        steps = data.get("steps") if isinstance(data, dict) else []
        steps = _normalize(steps, goal, base_url, registry, max_steps)
        return {"ok": True, "mode": "llm", "steps": steps}
    except Exception as exc:  # noqa: BLE001 - fallback is intentional
        result = _fallback(goal)
        result["steps"] = _normalize(result["steps"], goal, base_url, registry, max_steps)
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def _normalize(steps: Any, goal: str, base_url: str, registry, max_steps: int) -> list[dict]:
    allowed = {t.id for t in registry.for_profile("main")}
    out = []
    for step in (steps or [])[:max_steps]:
        if not isinstance(step, dict):
            continue
        tool = str(step.get("tool") or "")
        if tool not in allowed:
            continue
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        if tool in {"node.health", "node.version", "task.list"}:
            args.setdefault("base_url", base_url)
        out.append({"tool": tool, "args": args})
    return out


def to_package(goal: str, node_id: str, steps: list[dict], acceptance: list[str] | None = None) -> TaskPackage:
    return TaskPackage(goal=goal, node_id=node_id, steps=steps,
                       acceptance=acceptance or ["planned steps complete"],
                       tools_allowed=[s["tool"] for s in steps])
