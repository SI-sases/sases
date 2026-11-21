# core/services/model_service.py
import json
import secrets
import string
from ..db import db_cursor
from ..security import encrypt_api_key

PROVIDER_CAPABILITIES = {
    'deepseek': {'supports_vision': True, 'supports_image_edit': False, 'supports_video': False},
    'openai':   {'supports_vision': True, 'supports_image_edit': True,  'supports_video': False},
    'moonshot': {'supports_vision': False, 'supports_image_edit': False, 'supports_video': False},
    'zhipu':    {'supports_vision': True, 'supports_image_edit': True,  'supports_video': True},
    'qwen':     {'supports_vision': True, 'supports_image_edit': False, 'supports_video': False},
}

DEFAULT_CAPABILITIES = {'supports_vision': False, 'supports_image_edit': False, 'supports_video': False}

def generate_model_id(prefix: str) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return f"{prefix}_{''.join(secrets.choice(alphabet) for _ in range(8))}"

def create_api_key_model(user_id: int, name: str, provider: str, api_key: str, priority: int = 1):
    """添加 API Key 类型的模型配置"""
    encrypted = encrypt_api_key(api_key)
    model_id = generate_model_id("sases_api")
    with db_cursor(commit=True) as cur:
        _pkey = (provider or '').lower().strip()
        _caps = json.dumps(PROVIDER_CAPABILITIES.get(_pkey, DEFAULT_CAPABILITIES.copy()), ensure_ascii=False)
        cur.execute("""
            INSERT INTO model_configs (id, user_id, model_type, name, provider, api_key_encrypted, capabilities)
            VALUES (?, ?, 'api', ?, ?, ?, ?)
        """, (model_id, user_id, name, provider, encrypted, _caps))
    return model_id

def create_local_model(user_id: int, name: str, node_url: str, model_name: str, capabilities: str = None):
    """添加本地模型类型的模型配置"""
    model_id = generate_model_id("sases_node")
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO model_configs (id, user_id, model_type, name, node_url, model_name, capabilities)
            VALUES (?, ?, 'local', ?, ?, ?, ?)
        """, (model_id, user_id, name, node_url, model_name, capabilities))
    return model_id

def get_user_models(user_id: int):
    """获取用户所有模型配置"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, model_type, name, provider, node_url, model_name, capabilities, is_shared, visibility, price
            FROM model_configs
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def update_model_share(user_id: int, model_id: str, is_shared: int, visibility: str, price: float):
    """更新模型共享设置"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE model_configs
            SET is_shared=?, visibility=?, price=?
            WHERE id=? AND user_id=?
        """, (is_shared, visibility, price, model_id, user_id))
    return True

def update_model(user_id: int, model_id: str, name=None, provider=None, api_key=None,
                 node_url=None, model_name=None):
    """更新模型/智能体配置；api_key 为空表示不修改。"""
    fields, params = [], []
    if name is not None and str(name).strip():
        fields.append("name=?")
        params.append(str(name).strip())
    if provider is not None and str(provider).strip():
        fields.append("provider=?")
        params.append(str(provider).strip())
        _pkey = str(provider).lower().strip()
        fields.append("capabilities=?")
        params.append(json.dumps(PROVIDER_CAPABILITIES.get(_pkey, DEFAULT_CAPABILITIES.copy()), ensure_ascii=False))
    if api_key is not None and str(api_key).strip():
        fields.append("api_key_encrypted=?")
        params.append(encrypt_api_key(str(api_key).strip()))
    if node_url is not None and str(node_url).strip():
        fields.append("node_url=?")
        params.append(str(node_url).strip())
    if model_name is not None and str(model_name).strip():
        fields.append("model_name=?")
        params.append(str(model_name).strip())
    if not fields:
        return False
    params.extend([model_id, user_id])
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE model_configs SET " + ", ".join(fields) + " WHERE id=? AND user_id=?", tuple(params))
        return cur.rowcount > 0


def _table_exists(cur, name: str) -> bool:
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
        return cur.fetchone() is not None
    except Exception:
        return False


def get_model_refs(user_id: int, model_id: str):
    with db_cursor() as cur:
        cur.execute("SELECT id FROM model_configs WHERE id=? AND user_id=?", (model_id, user_id))
        if not cur.fetchone():
            return None
        refs = {}
        cur.execute("SELECT COUNT(*) FROM conversations WHERE agent_id=?", (model_id,))
        refs["conversations"] = cur.fetchone()[0]
        for table, col in (("group_members", "agent_id"), ("group_resource_pool", "agent_id"),
                           ("group_resource_pool", "model_id"), ("agent_friendships", "friend_agent_id")):
            if _table_exists(cur, table):
                try:
                    cur.execute("SELECT COUNT(*) FROM " + table + " WHERE " + col + "=?", (model_id,))
                    refs[table + "." + col] = cur.fetchone()[0]
                except Exception:
                    pass
        return refs


def delete_model(user_id: int, model_id: str):
    """删除模型配置（级联清理会话/群/好友引用）。"""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM model_configs WHERE id=? AND user_id=?", (model_id, user_id))
        row = cur.fetchone()
        if not row:
            return {"status": "ok", "deleted": False}
        cur.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE agent_id=?)", (model_id,))
        cur.execute("DELETE FROM conversations WHERE agent_id=?", (model_id,))
        for table, col in (("group_members", "agent_id"), ("group_resource_pool", "agent_id"),
                           ("group_resource_pool", "model_id"), ("agent_friendships", "friend_agent_id")):
            if _table_exists(cur, table):
                try:
                    cur.execute("DELETE FROM " + table + " WHERE " + col + "=?", (model_id,))
                except Exception as _e:
                    print("[model] 清理引用失败 %s.%s: %s" % (table, col, _e))
        cur.execute("DELETE FROM model_configs WHERE id=? AND user_id=?", (model_id, user_id))
    return {"status": "ok", "deleted": True}

def parse_capabilities(model_config) -> dict:
    """解析 model_config 的 capabilities 字段，返回 dict"""
    if not isinstance(model_config, dict):
        return DEFAULT_CAPABILITIES.copy()
    caps = model_config.get('capabilities')
    if not caps:
        return DEFAULT_CAPABILITIES.copy()
    try:
        result = json.loads(caps)
        for k, v in DEFAULT_CAPABILITIES.items():
            result.setdefault(k, v)
        return result
    except Exception:
        return DEFAULT_CAPABILITIES.copy()
