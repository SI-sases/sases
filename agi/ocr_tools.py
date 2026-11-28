"""Image OCR through the configured vision model."""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.request

from .fs_tools import _safe


def _vision_text(img) -> dict:
    url = os.environ.get("SASES_VISION_URL", "").strip()
    if not url:
        return {"ok": False, "error": "vision_not_configured"}
    img = img.convert("RGB")
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
    return {"ok": True, "text": str(data["choices"][0]["message"]["content"] or "")}




def pdf(args: dict) -> dict:
    try:
        from .fs_tools import _safe
        path = _safe(args.get("path") or "")
        if not path.is_file():
            return {"ok": False, "error": "not a file"}
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(path))
        max_pages = max(1, min(int(args.get("max_pages") or 3), 20))
        pages = []
        for i in range(min(len(doc), max_pages)):
            bitmap = doc[i].render(scale=max(1, min(int(args.get("dpi") or 150), 220)) / 72)
            img = bitmap.to_pil()
            out = _vision_text(img)
            if not out.get("ok"):
                return out
            pages.append(out.get("text") or "")
        return {"ok": True, "path": str(path), "pages": len(pages),
                "text": "\n".join(pages)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
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
