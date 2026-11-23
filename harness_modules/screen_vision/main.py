import base64
import os
import tempfile

from PIL import ImageGrab

from core import config
from core.seed_utils import call_chat


def _capture_png() -> str:
    image = ImageGrab.grab(all_screens=True)
    path = os.path.join(tempfile.gettempdir(), "sases_screen_vision.png")
    image.save(path, format="PNG")
    return path


def _image_base64(path: str) -> str:
    with open(path, "rb") as handle:
        raw = handle.read()
    if len(raw) > config.MAX_IMAGE_SIZE:
        raise ValueError("图片超过 MAX_IMAGE_SIZE 限制")
    return base64.b64encode(raw).decode("ascii")


def run(params):
    prompt = str(params.get("prompt") or (
        "分析这张屏幕截图。输出 JSON："
        '{"summary":"画面说明","elements":[{"label":"控件名","x":123,"y":456}]}。'
        "坐标使用图片像素坐标，只列出确实可见的控件。"
    ))
    image_path = params.get("image_path")
    if not image_path or params.get("capture"):
        image_path = _capture_png()
    if not os.path.isfile(image_path):
        raise FileNotFoundError(image_path)

    if not params.get("user_id") and not config.DEEPSEEK_API_KEY:
        raise ValueError("未配置视觉 API Key：请设置 DEEPSEEK_API_KEY 或传入 user_id")
    answer = call_chat(
        prompt,
        image_base64=_image_base64(image_path),
        user_id=params.get("user_id"),
        model=params.get("model") or config.VISION_MODEL_NAME,
        temperature=float(params.get("temperature") or 0.1),
    )
    return {"answer": answer, "image_path": image_path}
