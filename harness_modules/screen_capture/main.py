import base64
import io
import os
import time

from PIL import ImageGrab


def enable_dpi_awareness():
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _bbox(value):
    if not value:
        return None
    if isinstance(value, dict):
        left = int(value.get("left", value.get("x", 0)))
        top = int(value.get("top", value.get("y", 0)))
        width = int(value.get("width", 0))
        height = int(value.get("height", 0))
    else:
        left, top, width, height = [int(v) for v in value]
    if width <= 0 or height <= 0:
        raise ValueError("region width/height must be positive")
    return (left, top, left + width, top + height)


def run(params):
    enable_dpi_awareness()
    image = ImageGrab.grab(bbox=_bbox(params.get("region")), all_screens=True)
    original_width, original_height = image.width, image.height
    scale = float(params.get("scale") or 1.0)
    if 0 < scale < 1:
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))))

    save_path = params.get("save_path")
    if not save_path:
        root = os.path.join(os.getcwd(), "data", "screenshots")
        os.makedirs(root, exist_ok=True)
        save_path = os.path.join(root, time.strftime("screen_%Y%m%d_%H%M%S.png"))
    else:
        save_path = os.path.abspath(save_path)
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)

    image.save(save_path, format="PNG")
    result = {
        "path": save_path,
        "width": image.width,
        "height": image.height,
        "original_width": original_width,
        "original_height": original_height,
        "scale": scale,
        "size": os.path.getsize(save_path),
    }
    if params.get("return_base64"):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        result["base64"] = base64.b64encode(buffer.getvalue()).decode("ascii")
    return result
