"""Image OCR through the configured vision model."""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.request

from .fs_tools import _safe


def image(args: dict) -> dict:
    url = os.environ.get("SASES_VISION_URL", "").strip()
    if not url:
        return {"ok": False, "error": "vision_not_configured"}
    try:
        path = _safe(args.get("path") or "")
        from PIL import Image
        with Image.open(str(path)) as raw:
            img = raw.convert("RGB")
            img.thumbnail((1600, 1600))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
        payload = base64.b64encode(buffer.getvalue()).decode("ascii")
        body = {
            "model": os.environ.get("SASES_VISION_MODEL", "vision"),
            "temperature": 1,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Extract all visible text from this image. "
                                          "Return plain text only, preserve line breaks."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + payload}},
            ]}],
        }
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + os.environ.get("SASES_VISION_KEY", "")},
        )
        with urllib.request.urlopen(req, timeout=int(os.environ.get("SASES_VISION_TIMEOUT", "60"))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = str(data["choices"][0]["message"]["content"] or "")
        return {"ok": True, "path": str(path), "text": text}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
