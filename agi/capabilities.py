"""Role policy manifest for the shared main/sub tool registry.

One registry is intentional.  This module makes the boundary explicit and
testable: control-plane tools are main-only, local bridge tools are main-only,
and the sub AGI gets execution tools only.
"""
from __future__ import annotations

CONTROL_PLANE = {
    "adapter.list", "adapter.run", "deploy.stage", "deploy.verify",
    "deploy.promote", "deploy.rollback", "mcp.call", "mcp.servers",
    "mcp.tools", "plugin.list", "plugin.run", "planner.plan",
    "recovery.plan", "task.create", "workflow.run",
}

LOCAL_ONLY = {
    "local.fs.list", "local.fs.read", "local.fs.grep", "local.fs.glob",
    "local.fs.write", "local.fs.edit", "local.fs.mkdir", "local.fs.copy",
    "local.fs.move", "local.fs.delete", "local.shell.run", "local.shell.write",
    "local.office.read", "local.pdf.read", "local.image.read",
}

# Execution tools a sub AGI may use.  Anything not listed stays main-only.
SUB_ALLOWED_PREFIXES = ("browser.", "fs.", "office.", "pdf.", "image.", "shell.run", "skill.")


def check(registry) -> dict:
    violations = []
    for spec in registry._tools.values():  # noqa: SLF001 - policy audit
        if spec.id in CONTROL_PLANE and "sub" in spec.profiles:
            violations.append({"tool": spec.id, "reason": "control plane exposed to sub"})
        if spec.id in LOCAL_ONLY and "sub" in spec.profiles:
            violations.append({"tool": spec.id, "reason": "local bridge exposed to sub"})
    return {"ok": not violations, "violations": violations,
            "control_plane": sorted(CONTROL_PLANE), "local_only": sorted(LOCAL_ONLY)}


def list_manifest(registry) -> dict:
    rows = []
    for spec in registry.for_profile("main"):
        rows.append({"id": spec.id, "risk": spec.risk,
                     "profiles": sorted(spec.profiles),
                     "control_plane": spec.id in CONTROL_PLANE,
                     "local_only": spec.id in LOCAL_ONLY})
    return {"ok": True, "tools": rows, "audit": check(registry)}
