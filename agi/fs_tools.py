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


def _create_write_approval(tool: str, args: dict) -> dict:
    try:
        import sqlite3
        from . import approvals
        path = os.environ.get("SASES_AGI_DB", str(Path("data") / "agi.db"))
        conn = sqlite3.connect(path)
        try:
            approval_id = approvals.create(
                conn, tool, {k: v for k, v in args.items() if not k.startswith("_")},
                f"{tool}: {args.get('path') or ''}", risk="write",
            )
        finally:
            conn.close()
        return {"ok": False, "error": "approval_required", "tool": tool,
                "approval_id": approval_id}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"approval failed: {exc}", "tool": tool}


def write_file(args: dict) -> dict:
    if not args.get("_approved"):
        return _create_write_approval("fs.write", args)
    try:
        target = _safe(args.get("path") or "")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = str(args.get("content") or "")
        if target.exists() and not args.get("overwrite"):
            return {"ok": False, "error": "file exists; overwrite=true required"}
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(target), "bytes": len(content.encode("utf-8"))}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def edit_file(args: dict) -> dict:
    if not args.get("_approved"):
        return _create_write_approval("fs.edit", args)
    try:
        target = _safe(args.get("path") or "")
        old = str(args.get("old") or "")
        new = str(args.get("new") or "")
        text = target.read_text(encoding="utf-8")
        if old not in text:
            return {"ok": False, "error": "old text not found"}
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return {"ok": True, "path": str(target)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def mkdir(args: dict) -> dict:
    if not args.get("_approved"):
        return _create_write_approval("fs.mkdir", args)
    try:
        target = _safe(args.get("path") or "")
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def copy_path(args: dict) -> dict:
    if not args.get("_approved"):
        return _create_write_approval("fs.copy", args)
    try:
        import shutil
        src = _safe(args.get("src") or "")
        dst = _safe(args.get("dst") or "")
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return {"ok": True, "src": str(src), "dst": str(dst)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def move_path(args: dict) -> dict:
    if not args.get("_approved"):
        return _create_write_approval("fs.move", args)
    try:
        import shutil
        src = _safe(args.get("src") or "")
        dst = _safe(args.get("dst") or "")
        shutil.move(str(src), str(dst))
        return {"ok": True, "src": str(src), "dst": str(dst)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def delete_path(args: dict) -> dict:
    if not args.get("_approved"):
        return _create_write_approval("fs.delete", args)
    try:
        import shutil
        target = _safe(args.get("path") or "")
        if target == _root():
            return {"ok": False, "error": "cannot delete workspace root"}
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        return {"ok": True, "path": str(target)}
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
