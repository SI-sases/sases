"""Read-only filesystem tools for the main AGI.

All paths are constrained to SASES_FS_ROOT. Sensitive files and directories
are denied even if they are inside the root.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path


def _root() -> Path:
    return Path(os.environ.get("SASES_FS_ROOT", os.getcwd())).resolve()


def _safe(path: str) -> Path:
    target = (_root() / str(path or ".")).resolve() if not os.path.isabs(str(path)) else Path(path).resolve()
    if target != _root() and _root() not in target.parents:
        raise PermissionError("path escapes SASES_FS_ROOT")
    parts = {p.lower() for p in target.parts}
    if parts & {".git", "node_modules", "venv312", "__pycache__"}:
        raise PermissionError("sensitive directory")
    name = target.name.lower()
    if name in {".env", "users.db", "agi.fleet.token", "agi.token"}:
        raise PermissionError("sensitive file")
    if name.endswith((".token", ".key", ".pem", ".p12")):
        raise PermissionError("sensitive file")
    return target


def list_dir(args: dict) -> dict:
    try:
        target = _safe(args.get("path") or ".")
        if not target.is_dir():
            return {"ok": False, "error": "not a directory"}
        rows = []
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower())[:200]:
            try:
                rows.append({"name": item.name, "dir": item.is_dir(),
                             "size": item.stat().st_size if item.is_file() else 0})
            except OSError:
                continue
        return {"ok": True, "root": str(_root()), "path": str(target), "entries": rows}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def read_file(args: dict) -> dict:
    try:
        target = _safe(args.get("path") or "")
        if not target.is_file():
            return {"ok": False, "error": "not a file"}
        max_bytes = max(1, min(int(args.get("max_bytes") or 64000), 512000))
        raw = target.read_bytes()
        if b"\x00" in raw[:4096]:
            return {"ok": False, "error": "binary file"}
        text = raw[:max_bytes].decode("utf-8", errors="replace")
        return {"ok": True, "path": str(target), "text": text,
                "truncated": len(raw) > max_bytes, "bytes": len(raw)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def grep(args: dict) -> dict:
    try:
        target = _safe(args.get("path") or ".")
        pattern = re.compile(str(args.get("pattern") or ""))
        glob = str(args.get("glob") or "*.py")
        limit = max(1, min(int(args.get("max_matches") or 100), 500))
        matches = []
        files = [target] if target.is_file() else [
            p for p in target.rglob("*") if p.is_file() and fnmatch.fnmatch(p.name, glob)
        ]
        for path in files[:2000]:
            if len(matches) >= limit:
                break
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if pattern.search(line):
                        matches.append({"path": str(path), "line": number, "text": line[:300]})
                        if len(matches) >= limit:
                            break
            except (OSError, ValueError):
                continue
        return {"ok": True, "matches": matches, "truncated": len(matches) >= limit}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def glob_files(args: dict) -> dict:
    try:
        target = _safe(args.get("path") or ".")
        pattern = str(args.get("pattern") or "**/*")
        limit = max(1, min(int(args.get("limit") or 200), 1000))
        rows = [str(p) for p in target.glob(pattern) if p.is_file()][:limit]
        return {"ok": True, "files": rows, "truncated": len(rows) >= limit}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
