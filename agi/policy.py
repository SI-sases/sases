"""Who handles what: main AGI first, human commander only for exceptions."""
from __future__ import annotations

# Actions the main AGI may take without waking the commander.
MAIN_AUTO = {
    "health.observe",
    "event.record",
    "report.generate",
    "task.retry",
    "task.reroute",
    "config.low_risk",
    "staging.verify",
}

# Actions that always need the commander, even if the main AGI can plan them.
HUMAN_REQUIRED = {
    "code.change",
    "db.migration",
    "deploy.promote",
    "deploy.rollback",
    "service.restart.production",
    "security.change",
    "network.change",
    "billing.change",
    "unknown",
}


def classify(action: str, severity: str = "info", repeated: int = 1) -> dict:
    action = (action or "unknown").strip()
    severity = (severity or "info").strip()
    if action in HUMAN_REQUIRED:
        return {"owner": "human", "auto": False, "reason": "high-risk action"}
    if severity == "critical":
        return {"owner": "human", "auto": False, "reason": "critical severity"}
    if severity == "error" and repeated >= 3:
        return {"owner": "human", "auto": False, "reason": "repeated error"}
    if action in MAIN_AUTO:
        return {"owner": "main", "auto": True, "reason": "routine"}
    return {"owner": "main", "auto": False, "reason": "unknown action, observe only"}
