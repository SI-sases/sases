import base64
import json
import httpx
from typing import Optional
from ...security import decrypt_api_key, normalize_provider

async def call_model_with_config(model_config: dict, query: str) -> str:
    try:
        if model_config["model_type"] == "api":
            provider = normalize_provider(model_config["provider"])
            api_key = decrypt_api_key(model_config["api_key_encrypted"])
            if not api_key:
                raise Exception("API Key 解密失败")

            if provider == "deepseek":
                api_base = "https://api.deepseek.com/v1"
                model_name = "deepseek-chat"
            elif provider == "moonshot":
                api_base = "https://api.moonshot.cn/v1"
                model_name = "moonshot-v1-8k"
            elif provider == "openai":
                api_base = "https://api.openai.com/v1"
                model_name = "gpt-3.5-turbo"
            else:
                raise Exception(f"不支持的供应商: {provider}")

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": [{"role": "user", "content": query}], "temperature": 0.7}
                )
                if resp.status_code != 200:
                    raise Exception(f"上游API错误 ({resp.status_code}): {resp.text}")
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        elif model_config["model_type"] == "local":
            node_url = model_config["node_url"].rstrip("/")
            model_name = model_config["model_name"]
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{node_url}/api/generate",
                    json={"model": model_name, "prompt": query, "stream": False}
                )
                if resp.status_code != 200:
                    raise Exception(f"本地模型错误 ({resp.status_code}): {resp.text}")
                data = resp.json()
                return data.get("response", "")

        else:
            raise Exception("未知模型类型")
    except Exception as e:
        raise e

