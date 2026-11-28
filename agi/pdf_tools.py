"""Read-only PDF text extraction."""
from __future__ import annotations

from .fs_tools import _safe


def read(args: dict) -> dict:
    try:
        path = _safe(args.get("path") or "")
        if not path.is_file():
            return {"ok": False, "error": "not a file"}
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        limit = max(1, min(int(args.get("max_chars") or 20000), 100000))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return {"ok": True, "path": str(path), "pages": len(reader.pages),
                "text": text[:limit], "truncated": len(text) > limit}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
