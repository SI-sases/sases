"""Bounded investigation loop for the main AGI.

The loop can run in two modes:
- planner mode: planner returns a read-only step list (default, cheap)
- step mode: a decide callback is asked for the next action after every result

Only read-risk tools are eligible in this loop.
"""
from __future__ import annotations

import json
import os

from .planner import plan


def _read_tools(registry) -> list[dict]:
    return [{"id": t.id, "description": t.description}
            for t in registry.for_profile("main") if t.risk == "read"]


def _llm_decide(goal: str, trace: list[dict], registry) -> dict:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key or api_key.startswith("sk-dummy"):
        return {"ok": False, "error": "model unavailable"}
    try:
        from openai import OpenAI
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model_name = os.environ.get("MODEL_NAME", "deepseek-chat")
        client = OpenAI(api_key=api_key, base_url=base_url)
        prompt = (
            "You are the SASES main AGI investigator. Choose exactly one next read-only tool "
            'or finish. Return JSON only: {"done":true} or '
            '{"done":false,"tool":"tool.id","args":{}}. '
            "Only use these tools: %s\nGoal: %s\nTrace: %s"
            % (json.dumps(_read_tools(registry), ensure_ascii=False), goal,
               json.dumps([{"tool": t["tool"], "ok": t["ok"]} for t in trace], ensure_ascii=False))
        )
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": "Return JSON only."},
                      {"role": "user", "content": prompt}],
            temperature=0, max_tokens=300, timeout=20,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.strip("`").replace("json\n", "", 1).strip()
        data = json.loads(text)
        return {"ok": True, **data}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run(goal: str, registry, base_url: str = "http://127.0.0.1:8001",
        max_steps: int = 6, decide=None) -> dict:
    trace = []
    allowed = {t["id"] for t in _read_tools(registry)}
    if decide is None:
        planned = plan(goal, registry, base_url, max_steps)
        steps = list(planned.get("steps") or [])
        for step in steps[:max_steps]:
            tool = str(step.get("tool") or "")
            args = step.get("args") if isinstance(step.get("args"), dict) else {}
            try:
                result = registry.invoke("main", tool, args)
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            trace.append({"tool": tool, "args": args, "ok": bool(result.get("ok")), "result": result})
        return {"ok": all(t["ok"] for t in trace), "mode": planned.get("mode"),
                "steps": trace, "summary": f"executed {len(trace)} read-only steps"}

    mode = "step"
    seen_actions: set[str] = set()
    for _ in range(max_steps):
        decision = decide(goal, trace, registry)
        if not decision.get("ok"):
            if not trace:
                planned = plan(goal, registry, base_url, max_steps)
                for step in list(planned.get("steps") or [])[:max_steps]:
                    tool = str(step.get("tool") or "")
                    args = step.get("args") if isinstance(step.get("args"), dict) else {}
                    try:
                        result = registry.invoke("main", tool, args)
                    except Exception as exc:  # noqa: BLE001
                        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    trace.append({"tool": tool, "args": args, "ok": bool(result.get("ok")), "result": result})
                return {"ok": all(t["ok"] for t in trace), "mode": "step+fallback",
                        "steps": trace, "error": decision.get("error") or "",
                        "summary": f"executed {len(trace)} read-only steps"}
            return {"ok": False, "mode": mode, "steps": trace,
                    "error": decision.get("error") or "decision failed"}
        if decision.get("done"):
            if not trace:
                planned = plan(goal, registry, base_url, max_steps)
                for step in list(planned.get("steps") or [])[:max_steps]:
                    tool = str(step.get("tool") or "")
                    args = step.get("args") if isinstance(step.get("args"), dict) else {}
                    try:
                        result = registry.invoke("main", tool, args)
                    except Exception as exc:  # noqa: BLE001
                        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    trace.append({"tool": tool, "args": args, "ok": bool(result.get("ok")), "result": result})
            break
        tool = str(decision.get("tool") or "")
        args = decision.get("args") if isinstance(decision.get("args"), dict) else {}
        if tool not in allowed:
            return {"ok": False, "mode": mode, "steps": trace,
                    "error": f"tool not allowed in read-only loop: {tool}"}
        action_key = tool + ":" + json.dumps(args, ensure_ascii=False, sort_keys=True)
        if action_key in seen_actions:
            break
        seen_actions.add(action_key)
        try:
            result = registry.invoke("main", tool, args)
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        trace.append({"tool": tool, "args": args, "ok": bool(result.get("ok")), "result": result})
        if not result.get("ok"):
            break
    if "readme" in goal.lower() and not any(t.get("tool") == "fs.read" for t in trace):
        try:
            result = registry.invoke("main", "fs.read", {"path": "README.md"})
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        trace.append({"tool": "fs.read", "args": {"path": "README.md"},
                      "ok": bool(result.get("ok")), "result": result})
    return {"ok": all(t["ok"] for t in trace), "mode": mode,
            "steps": trace, "summary": f"executed {len(trace)} read-only steps"}


def markdown(result: dict) -> str:
    lines = ["## 主 AGI 调查", "", f"模式：**{result.get('mode', 'unknown')}**", ""]
    for i, item in enumerate(result.get("steps") or [], 1):
        status = "ok" if item.get("ok") else "failed"
        lines.append(f"{i}. `{item.get('tool')}` → {status}")
        if not item.get("ok"):
            lines.append("   - " + str((item.get("result") or {}).get("error") or "unknown")[:200])
    lines += ["", "**只执行只读工具，未写入任何文件。**"]
    return "\n".join(lines)
