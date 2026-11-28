"""Bounded investigation loop for the main AGI.

The planner chooses read-only tool calls; the loop executes them one by one,
records a trace, and replans once after a failure. It never contains write or
shell tools in this version.
"""
from __future__ import annotations

from .planner import plan


def run(goal: str, registry, base_url: str = "http://127.0.0.1:8001",
        max_steps: int = 6) -> dict:
    trace = []
    planned = plan(goal, registry, base_url, max_steps)
    steps = list(planned.get("steps") or [])
    failures = 0
    for step in steps[:max_steps]:
        tool = str(step.get("tool") or "")
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        try:
            result = registry.invoke("main", tool, args)
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        trace.append({"tool": tool, "args": args, "ok": bool(result.get("ok")), "result": result})
        if not result.get("ok"):
            failures += 1
            if failures >= 2:
                break
            replanned = plan(goal + "\nPrevious failure: " + str(result.get("error") or ""),
                             registry, base_url, max_steps - len(trace))
            steps = list(replanned.get("steps") or [])
    return {"ok": failures == 0, "mode": planned.get("mode"), "steps": trace,
            "summary": f"executed {len(trace)} read-only steps"}


def markdown(result: dict) -> str:
    lines = ["## 主 AGI 调查", "", f"模式：**{result.get('mode', 'unknown')}**", ""]
    for i, item in enumerate(result.get("steps") or [], 1):
        status = "ok" if item.get("ok") else "failed"
        lines.append(f"{i}. `{item.get('tool')}` → {status}")
        if not item.get("ok"):
            lines.append("   - " + str((item.get("result") or {}).get("error") or "unknown")[:200])
    lines += ["", "**只执行只读工具，未写入任何文件。**"]
    return "\n".join(lines)
