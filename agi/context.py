"""Compact AGI context before sending it to a sub AGI."""
from __future__ import annotations


def compact(events: list[dict], max_chars: int = 4000) -> str:
    total = len(events)
    by_severity: dict[str, int] = {}
    for event in events:
        sev = str(event.get("severity") or "info")
        by_severity[sev] = by_severity.get(sev, 0) + 1
    lines = ["## Context summary", f"- events: {total}"]
    for sev in ("critical", "error", "warning", "info"):
        if by_severity.get(sev):
            lines.append(f"- {sev}: {by_severity[sev]}")
    errors = [e for e in events if e.get("severity") in ("error", "critical")][-10:]
    if errors:
        lines.append("\n## Recent errors")
        for event in errors:
            lines.append(f"- {event.get('node_id', '-')}: {event.get('message', '')[:160]}")
    text = "\n".join(lines)
    return text[:max_chars]
