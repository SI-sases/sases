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


def choose_element(screenshot: str, instruction: str, elements: list[dict]) -> dict:
    """Annotate element boxes and ask the vision model for an index."""
    url = os.environ.get("SASES_VISION_URL", "").strip()
    if not url:
        return {"ok": False, "error": "vision_not_configured"}
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        with Image.open(screenshot) as raw:
            image = raw.convert("RGB")
            original_size = image.size
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()
            for index, element in enumerate(elements):
                box = element.get("bbox") or []
                if len(box) != 4:
                    continue
                x, y, w, h = [int(v) for v in box]
                draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=3)
                draw.text((x + 4, y + 4), str(index), fill=(255, 0, 0), font=font)
            image.thumbnail((1280, 1280))
            sent_size = image.size
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=82)
        payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"annotate_error: {exc}"}
    prompt = (instruction + f" The image size is {sent_size[0]}x{sent_size[1]}. "
              "Choose one numbered red box. Return only JSON {\"index\": int}.")
    body = {"model": os.environ.get("SASES_VISION_MODEL", "vision"), "temperature": 1,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + payload}}]}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + os.environ.get("SASES_VISION_KEY", "")})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        parsed = json.loads(content[start:end + 1])
        return {"ok": True, "index": int(parsed["index"])}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


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
            image_obj.thumbnail((1280, 1280))
            sent_size = image_obj.size
            buffer = io.BytesIO()
            image_obj.save(buffer, format="JPEG", quality=82)
        image = base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"screenshot_error: {exc}"}
    body = {
        "model": os.environ.get("SASES_VISION_MODEL", "vision"),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": instruction + f" Image size is {sent_size[0]}x{sent_size[1]}. Return only JSON {{\"x\": int, \"y\": int}} in those pixel coordinates."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image}},
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
