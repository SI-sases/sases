"""Optional vision-model target locator.

Disabled unless SASES_VISION_URL is configured. The endpoint is expected to
accept an OpenAI-compatible chat-completions request with one image message
and return JSON containing {"x": number, "y": number}.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request


def configured() -> bool:
    return bool(os.environ.get("SASES_VISION_URL", "").strip())


def locate(screenshot: str, instruction: str) -> dict:
    url = os.environ.get("SASES_VISION_URL", "").strip()
    if not url:
        return {"ok": False, "error": "vision_not_configured"}
    try:
        from PIL import Image
        import io
        with Image.open(screenshot) as raw:
            image_obj = raw.convert("RGB")
            original_size = image_obj.size
            image_obj.thumbnail((768, 768))
            sent_size = image_obj.size
            buffer = io.BytesIO()
            image_obj.save(buffer, format="JPEG", quality=75)
        image = base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"screenshot_error: {exc}"}
    body = {
        "model": os.environ.get("SASES_VISION_MODEL", "vision"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": instruction + ' Return only JSON {"x": int, "y": int}.'},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image}},
            ],
        }],
        "temperature": 1,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("SASES_VISION_KEY", "")},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8") or "{}")
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        start = content.find("{")
        end = content.rfind("}")
        data = json.loads(content[start:end + 1])
        scale_x = original_size[0] / max(1, sent_size[0])
        scale_y = original_size[1] / max(1, sent_size[1])
        return {"ok": True, "x": int(float(data["x"]) * scale_x),
                "y": int(float(data["y"]) * scale_y)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
