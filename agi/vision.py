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
        with open(screenshot, "rb") as handle:
            image = base64.b64encode(handle.read()).decode("ascii")
    except OSError as exc:
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
        "temperature": 0,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + os.environ.get("SASES_VISION_KEY", "")},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8") or "{}")
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        start = content.find("{")
        end = content.rfind("}")
        data = json.loads(content[start:end + 1])
        return {"ok": True, "x": int(data["x"]), "y": int(data["y"])}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
