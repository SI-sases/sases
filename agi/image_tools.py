"""Read-only image metadata extraction."""
from __future__ import annotations

from .fs_tools import _safe


def read(args: dict) -> dict:
    try:
        path = _safe(args.get("path") or "")
        if not path.is_file():
            return {"ok": False, "error": "not a file"}
        from PIL import Image
        with Image.open(str(path)) as img:
            return {"ok": True, "path": str(path), "format": img.format,
                    "width": img.width, "height": img.height, "mode": img.mode}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
