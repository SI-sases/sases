"""core/hive/config.py —— 蜂巢配置。

读取优先级（从高到低）：
  1. 环境变量（临时覆盖，优先级最高）
  2. hive-nodes/{node_id}/config.json（持久配置）
  3. 默认值

角色说明：
  master  —— 主节点，有完整业务数据，对外提供账本
  slave   —— 从节点，只同步 + 锚定
  peer    —— 对等节点（未来）

注意：NODE_ID 只从环境变量读（用它定位 config.json，鸡生蛋问题）。
"""
import os
import json

_NODE_ID = os.environ.get("SASES_NODE_ID", "node-A")
_JSON_CONFIG_PATH = os.path.join("hive-nodes", _NODE_ID, "config.json")


def _load_json_config():
    if os.path.exists(_JSON_CONFIG_PATH):
        try:
            with open(_JSON_CONFIG_PATH, encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"[hive-config] failed to load {_JSON_CONFIG_PATH}: {e}")
            return {}
    return {}


_JSON = _load_json_config()


def _get(key, env_key=None, default=None):
    env_key = env_key or key
    v = os.environ.get(env_key)
    if v not in (None, ""):
        return v
    if key in _JSON:
        return _JSON[key]
    return default


def _get_bool(key, env_key=None, default=False):
    v = _get(key, env_key, None)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes")


def _get_int(key, env_key=None, default=0):
    v = _get(key, env_key, None)
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _get_list(key, env_key=None):
    env_key = env_key or key
    v = os.environ.get(env_key)
    if v:
        return [x.strip().rstrip("/") for x in v.split(",") if x.strip()]
    if key in _JSON:
        raw = _JSON[key]
        if isinstance(raw, list):
            return [str(x).strip().rstrip("/") for x in raw if str(x).strip()]
        if isinstance(raw, str):
            return [x.strip().rstrip("/") for x in raw.split(",") if x.strip()]
    return []


# ========== 核心 ==========
ENABLE_HIVE = _get_bool("enable_hive", "ENABLE_HIVE", False)
HIVE_ROLE = str(_get("role", "HIVE_ROLE", "master")).lower()
NODE_ID = _NODE_ID

# ========== 主从同步 ==========
HIVE_MASTER = str(_get("master", "HIVE_MASTER", "")).rstrip("/")
HIVE_MASTERS = _get_list("masters", "HIVE_MASTERS")
if not HIVE_MASTERS and HIVE_MASTER:
    HIVE_MASTERS = [HIVE_MASTER]

HIVE_PEERS = _get_list("peers", "HIVE_PEERS")

# ========== 模式与安全 ==========
HIVE_MODE = str(_get("mode", "HIVE_MODE", "alert")).lower()
HIVE_TOKEN = str(_get("token", "HIVE_TOKEN", ""))
DEGRADE_THRESHOLD = _get_int("degrade_threshold", "HIVE_DEGRADE_THRESHOLD", 3)
REPLICA_MODE = _get_bool("replica_mode", "REPLICA_MODE", False)

# ========== 各任务周期（秒） ==========
ANCHOR_INTERVAL = _get_int("anchor_interval", "HIVE_ANCHOR_INTERVAL", 3600)
HEARTBEAT_INTERVAL = _get_int("heartbeat_interval", "HIVE_HEARTBEAT_INTERVAL", 60)
VOTE_INTERVAL = _get_int("vote_interval", "HIVE_VOTE_INTERVAL", 120)
SYNC_INTERVAL = _get_int("sync_interval", "HIVE_SYNC_INTERVAL", 30)
