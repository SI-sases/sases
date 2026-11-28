"""Read-only shell allowlist for main-AGI inspection."""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


ALLOWED = {"dir", "ls", "pwd", "echo", "type", "cat", "git"}
ALLOWED_WRITE = {"mkdir", "copy", "move"}
GIT_SUB = {"status", "log", "diff", "show", "rev-parse", "branch"}
FORBIDDEN = set("|;&><`$\\\n\r\t")


def _root() -> Path:
    return Path(os.environ.get("SASES_FS_ROOT", os.getcwd())).resolve()


def run(args: dict) -> dict:
    command = str(args.get("command") or "").strip()
    if not command:
        return {"ok": False, "error": "command is required"}
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return {"ok": False, "error": f"parse error: {exc}"}
    if not tokens:
        return {"ok": False, "error": "command is empty"}
    if tokens[0].lower() not in ALLOWED:
        return {"ok": False, "error": f"command not allowed: {tokens[0]}"}
    if tokens[0].lower() == "git" and (len(tokens) < 2 or tokens[1] not in GIT_SUB):
        return {"ok": False, "error": "git subcommand not allowed"}
    for token in tokens[1:]:
        if any(ch in FORBIDDEN for ch in token):
            return {"ok": False, "error": "unsafe character"}
    if tokens[0].lower() == "pwd":
        return {"ok": True, "returncode": 0, "output": str(_root()), "truncated": False,
                "cwd": str(_root())}
    cmd = tokens
    if os.name == "nt" and tokens[0].lower() in {"dir", "type", "echo"}:
        cmd = ["cmd.exe", "/d", "/c"] + tokens
    try:
        proc = subprocess.run(cmd, cwd=str(_root()), capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=max(1, min(int(args.get("timeout") or 10), 30)),
                              shell=False)
        output = (proc.stdout or "") + (proc.stderr or "")
        return {"ok": proc.returncode == 0, "returncode": proc.returncode,
                "output": output[:64000], "truncated": len(output) > 64000,
                "cwd": str(_root())}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_write(args: dict) -> dict:
    if not args.get("_approved"):
        from .fs_tools import _create_write_approval
        return _create_write_approval("shell.write", args)
    command = str(args.get("command") or "").strip()
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return {"ok": False, "error": f"parse error: {exc}"}
    if not tokens or tokens[0].lower() not in ALLOWED_WRITE:
        return {"ok": False, "error": "write command not allowed"}
    for token in tokens[1:]:
        if any(ch in FORBIDDEN for ch in token):
            return {"ok": False, "error": "unsafe character"}
    cmd = tokens
    if os.name == "nt" and tokens[0].lower() in {"mkdir", "copy", "move"}:
        cmd = ["cmd.exe", "/d", "/c"] + tokens
    try:
        proc = subprocess.run(cmd, cwd=str(_root()), capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=max(1, min(int(args.get("timeout") or 10), 30)), shell=False)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode,
                "output": ((proc.stdout or "") + (proc.stderr or ""))[:64000],
                "cwd": str(_root())}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
