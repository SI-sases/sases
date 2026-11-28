"""Present small artifacts as inline data URLs."""
from __future__ import annotations

import base64
import mimetypes

from .fs_tools import _safe


def present(args: dict) -> dict:
    try:
        path = _safe(args.get("path") or "")
        if not path.is_file():
            return {"ok": False, "error": "not a file"}
        raw = path.read_bytes()
        if len(raw) > 2_000_000:
            return {"ok": False, "error": "artifact too large; use a file path"}
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        return {"ok": True, "title": str(args.get("title") or path.name),
                "path": str(path), "mime": mime, "size": len(raw),
                "data_url": "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
