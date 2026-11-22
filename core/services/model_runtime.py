# core/services/model_runtime.py
# -*- coding: utf-8 -*-
"""按 agent_id 解析模型配置，供子智能体/多模型 loop 使用。"""
from ..db import db_cursor
from ..security import decrypt_api_key, normalize_provider


def resolve(user_id, agent_id):
    if not agent_id:
        return None
    with db_cursor() as cur:
        cur.execute("SELECT * FROM model_configs WHERE id=? AND user_id=?", (str(agent_id), int(user_id)))
        row = cur.fetchone()
    if not row:
        return None
    cfg = dict(row)
    if cfg.get("model_type") == "local":
        try:
            from openai import OpenAI
            base = str(cfg.get("node_url") or "").rstrip("/")
            model = str(cfg.get("model_name") or "")
            if not base or not model:
                return None
            return {"client": OpenAI(api_key="local", base_url=base + "/v1"),
                    "model": model, "agent_id": cfg.get("id"), "name": cfg.get("name") or model}
        except Exception as e:
            print("[model] local resolve 失败: " + str(e))
            return None
    if cfg.get("model_type") != "api":
        return None
    try:
        from openai import OpenAI
        provider = normalize_provider(cfg.get("provider"))
        key = decrypt_api_key(cfg.get("api_key_encrypted"))
        if not key:
            return None
        base = {
            "deepseek": "https://api.deepseek.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "openai": "https://api.openai.com/v1",
        }.get(provider)
        model = {
            "deepseek": "deepseek-chat",
            "moonshot": "moonshot-v1-8k",
            "openai": "gpt-3.5-turbo",
        }.get(provider, cfg.get("model_name") or "")
        if not base or not model:
            return None
        return {"client": OpenAI(api_key=key, base_url=base), "model": model,
                "agent_id": cfg.get("id"), "name": cfg.get("name") or model}
    except Exception as e:
        print("[model] resolve 失败: " + str(e))
        return None
