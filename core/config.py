# core/config.py
# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# ========== DeepSeek API 閰嶇疆锛堢郴缁熼粯璁わ級 ==========
def _get_db_api_key():
    try:
        import sqlite3
        _db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users.db")
        if os.path.exists(_db):
            _c = sqlite3.connect(_db)
            _row = _c.execute("SELECT api_key_encrypted FROM model_configs WHERE model_type IN ('api', 'api_key') LIMIT 1").fetchone()
            _c.close()
            if _row and _row[0]:
                from core.security import decrypt_api_key
                return decrypt_api_key(_row[0])
    except Exception:
        pass
    return ""

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or _get_db_api_key() or "sk-dummy-key-for-startup"
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v4-flash")

# ========== 铚傜兢/鑺傜偣鏍囪瘑 ==========
NODE_ID = os.environ.get("SASES_NODE_ID", "node-A")

# anchor-check: restart-signal-path-fix

# ========== Embedding 閰嶇疆锛堢敤浜庣煡璇嗗簱璇箟妫€绱級 ==========
# 浼樺厛鐢ㄤ笓鐢?Embedding API锛屾湭閰嶇疆鏃跺洖閫€鍒?DeepSeek 閰嶇疆
EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", DEEPSEEK_API_KEY)
EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", DEEPSEEK_BASE_URL)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "deepseek-embedding")

# ========== 瑙嗚/澶氭ā鎬佹ā鍨嬮厤缃?==========
VISION_MODEL_NAME = os.environ.get("VISION_MODEL_NAME", "deepseek-v4-flash-vision-exp")

VISION_MODEL_BY_PROVIDER = {
    "deepseek": {"model": "deepseek-v4-flash-vision-exp", "supports_image": True},
    "openai": {"model": "gpt-4o-mini", "supports_image": True},
    "moonshot": {"model": "", "supports_image": False},
    "zhipu": {"model": "glm-4v", "supports_image": True},
    "qwen": {"model": "qwen-vl-plus", "supports_image": True},
}
AUDIO_MODEL_BY_PROVIDER = {
    "openai": "whisper-1",
    "deepseek": "",
    "moonshot": "",
    "zhipu": "",
    "qwen": "",
}
VIDEO_MODEL_BY_PROVIDER = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-v4-flash-vision-exp",
    "moonshot": "",
    "zhipu": "glm-4v",
    "qwen": "qwen-vl-plus",
}

# ========== 鏂囦欢澶у皬闄愬埗 ==========
MAX_IMAGE_SIZE = int(os.environ.get("MAX_IMAGE_SIZE", 5 * 1024 * 1024))
MAX_AUDIO_SIZE = int(os.environ.get("MAX_AUDIO_SIZE", 10 * 1024 * 1024))
MAX_VIDEO_SIZE = int(os.environ.get("MAX_VIDEO_SIZE", 25 * 1024 * 1024))

# ========== 鎻愪緵鍟嗘槧灏?==========
PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}
PROVIDER_ALIASES = {
    "ds": "deepseek",
    "deepseek-chat": "deepseek",
    "gpt": "openai",
    "openai-chat": "openai",
    "moonshot-v1": "moonshot",
    "kimi": "moonshot",
    "glm": "zhipu",
    "chatglm": "zhipu",
    "qwen-turbo": "qwen",
    "tongyi": "qwen",
}

# ========== 瀹夊叏涓庡瘑閽?==========
SASES_SECRET_KEY = os.environ.get("SASES_SECRET_KEY", "sases-dev-secret-key")
SIGN_KEY_FILE = os.environ.get("SIGN_KEY_FILE", "secret_key.bin")
API_KEY_ENCRYPTION_KEY_FILE = os.environ.get("API_KEY_ENCRYPTION_KEY_FILE", "api_key_encryption.key")
NODE_TOKEN = os.environ.get("SASES_NODE_TOKEN", "")

# ========== 鏁版嵁搴撲笌鏂囦欢璺緞 ==========
DB_FILE = os.environ.get("DB_FILE", "users.db")
KB_FILE = os.environ.get("KB_FILE", "success_kb.json")
SEED_POOL_FILE = os.environ.get("SEED_POOL_FILE", "seed_tasks_external.jsonl")
MAIN_SEED_FILE = os.environ.get("MAIN_SEED_FILE", "seed_tasks_new.jsonl")
SHARED_LOG_FILE = os.environ.get("SHARED_LOG_FILE", "shared_pollinate_log.jsonl")
CONTRIBUTION_LOG_DB = os.environ.get("CONTRIBUTION_LOG_DB", "users.db")

# ========== 鐩镐技搴︿笌绉垎瑙勫垯 ==========
# 娉ㄦ剰锛歋IMILARITY_THRESHOLD 鏄棫鐗?TF-IDF 浣跨敤鐨勯槇鍊?
# 鏂扮増 knowledge_service 浣跨敤 embedding 鏃朵細鐢ㄧ嫭绔嬬殑闃堝€硷紝涓嶄娇鐢ㄨ繖涓€?
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.30"))
EXTERNAL_SEED_REWARD = int(os.environ.get("EXTERNAL_SEED_REWARD", "5"))
MANUAL_POLLINATE_BASIC_REWARD = int(os.environ.get("MANUAL_POLLINATE_BASIC_REWARD", "3"))
MANUAL_POLLINATE_EXPERT_REWARD = int(os.environ.get("MANUAL_POLLINATE_EXPERT_REWARD", "10"))
QUERY_DEDUCTION = int(os.environ.get("QUERY_DEDUCTION", "2"))

# ========== 鑺傜偣涓庡彂鐜?==========
NODE_ID = os.environ.get("SASES_NODE_ID", "node-001")
NODE_NAME = os.environ.get("SASES_NODE_NAME", "SASES Node")
PEER_NODES = [x.strip() for x in os.environ.get("SASES_PEERS", "").split(",") if x.strip()]

# mDNS 鍙戠幇
ENABLE_MDNS = os.environ.get("SASES_ENABLE_MDNS", "false").lower() == "true"
MDNS_SERVICE_TYPE = "_sases._tcp.local."

# ========== DashScope Embedding锛堢敤浜庢贩鍚堟ā寮忥級 ==========
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
DASHSCOPE_EMBEDDING_MODEL = os.environ.get(
    "DASHSCOPE_EMBEDDING_MODEL",
    "text-embedding-v3"
)

# Embedding 妯″紡锛歭ocal / api / hybrid
EMBEDDING_MODE = os.environ.get("EMBEDDING_MODE", "hybrid")

# 娣峰悎妯″紡鐨勮竟鐣岄槇鍊?
HYBRID_LOW_THRESHOLD = float(os.environ.get("HYBRID_LOW_THRESHOLD", "0.35"))
HYBRID_HIGH_THRESHOLD = float(os.environ.get("HYBRID_HIGH_THRESHOLD", "0.88"))

# ========== 鎸囨尌瀹?瀹℃牳鍛?LLM 鍙傛暟 ==========
COMMANDER_MAX_TOKENS = int(os.environ.get("COMMANDER_MAX_TOKENS", "30000"))
REPLAN_MAX_TOKENS = int(os.environ.get("REPLAN_MAX_TOKENS", "16000"))
SUMMARY_MAX_TOKENS = 41003

# ========== 铚傜兢妯″紡锛堥槻绡℃敼锛?==========
# off: 鍏抽棴锛堝崟鐢ㄦ埛锛岄粯璁わ級
# alert: 鍙憡璀︼紙鑱旈偊鏃╂湡锛屽淇′换鏂癸級
# enforce: 寮哄埗锛堢Н鍒嗘寕閽╃湡瀹炰环鍊兼椂锛?
HIVE_MODE = os.environ.get("SASES_HIVE_MODE", "off").lower().strip()
if HIVE_MODE not in ("off", "alert", "enforce"):
    HIVE_MODE = "off"

HIVE_PEERS = [x.strip() for x in os.environ.get("SASES_HIVE_PEERS", "").split(",") if x.strip()]
HIVE_NODE_ID = os.environ.get("SASES_HIVE_NODE_ID", "")
HIVE_ANCHOR_INTERVAL = int(os.environ.get("SASES_HIVE_ANCHOR_INTERVAL", "3600"))
HIVE_HEARTBEAT_INTERVAL = int(os.environ.get("SASES_HIVE_HEARTBEAT_INTERVAL", "300"))

# 姣忚疆鏈€澶ф媶瑙ｆ鏁帮紙鐜鍙橀噺鍙皟锛?
MAX_STEPS = int(os.environ.get("SASES_MAX_STEPS", "8"))

