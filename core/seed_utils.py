import openai
import base64
import time

from core import config
from core.utils.code_utils import is_python_code, clean_code, check_syntax, parse_two_branches
from core.utils.sandbox import safe_run_tests

# 默认客户端
_client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=120,
    max_retries=2
)

def _call_openai_with_key(provider: str, api_key: str, model: str, messages: list, temperature: float, max_retries: int):
    base_url = config.PROVIDER_BASE_URLS.get(provider, config.DEEPSEEK_BASE_URL)
    client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=120, max_retries=max_retries)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return resp.choices[0].message.content

def call_chat(prompt, max_retries=2, temperature=0.7, model=None, user_id=None, image_base64=None):
    if model is None:
        model = config.MODEL_NAME

    # 图片大小检查
    if image_base64:
        img_size = len(base64.b64decode(image_base64))
        if img_size > config.MAX_IMAGE_SIZE:
            raise ValueError("图片大小超过限制")

    messages = []
    if image_base64:
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt})

    # 如果提供了用户ID，尝试使用用户API Key
    if user_id is not None:
        try:
            from core import auth_service
            api_keys = auth_service.get_active_api_keys(user_id)
        except Exception:
            api_keys = []

        if api_keys:
            last_error = None
            for entry in api_keys:
                provider = config.PROVIDER_ALIASES.get(entry["provider"], entry["provider"])
                api_key = entry["key"]
                if image_base64:
                    vision_cfg = config.VISION_MODEL_BY_PROVIDER.get(provider)
                    if not vision_cfg or not vision_cfg.get("supports_image"):
                        continue
                    model_to_use = vision_cfg["model"]
                else:
                    model_to_use = model
                try:
                    return _call_openai_with_key(provider, api_key, model_to_use, messages, temperature, max_retries)
                except Exception as e:
                    last_error = e
                    print(f"Provider {provider} 调用失败: {e}")
                    continue
            if last_error:
                raise last_error

    # 回退到默认客户端
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = _client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"默认 API 调用失败（尝试 {attempt+1}/{max_retries+1}）：{e}")
            if attempt < max_retries:
                time.sleep(5)
    raise last_error
