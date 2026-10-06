# core/config.py
# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# ========== DeepSeek API 配置（系统默认） ==========
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-v4-flash")

# ========== 蜂群/节点标识 ==========
NODE_ID = os.environ.get("SASES_NODE_ID", "node-A")

# ========== Embedding 配置（用于知识库语义检索） ==========
# 优先用专用 Embedding API，未配置时回退到 DeepSeek 配置
EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", DEEPSEEK_API_KEY)
EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", DEEPSEEK_BASE_URL)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "deepseek-embedding")

# ========== 视觉/多模态模型配置 ==========
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

# ========== 文件大小限制 ==========
MAX_IMAGE_SIZE = int(os.environ.get("MAX_IMAGE_SIZE", 5 * 1024 * 1024))
MAX_AUDIO_SIZE = int(os.environ.get("MAX_AUDIO_SIZE", 10 * 1024 * 1024))
MAX_VIDEO_SIZE = int(os.environ.get("MAX_VIDEO_SIZE", 25 * 1024 * 1024))

# ========== 提供商映射 ==========
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

# ========== 安全与密钥 ==========
SASES_SECRET_KEY = os.environ.get("SASES_SECRET_KEY", "sases-dev-secret-key")
SIGN_KEY_FILE = os.environ.get("SIGN_KEY_FILE", "secret_key.bin")
API_KEY_ENCRYPTION_KEY_FILE = os.environ.get("API_KEY_ENCRYPTION_KEY_FILE", "api_key_encryption.key")
NODE_TOKEN = os.environ.get("SASES_NODE_TOKEN", "")

# ========== 数据库与文件路径 ==========
DB_FILE = os.environ.get("DB_FILE", "users.db")
KB_FILE = os.environ.get("KB_FILE", "success_kb.json")
SEED_POOL_FILE = os.environ.get("SEED_POOL_FILE", "seed_tasks_external.jsonl")
MAIN_SEED_FILE = os.environ.get("MAIN_SEED_FILE", "seed_tasks_new.jsonl")
SHARED_LOG_FILE = os.environ.get("SHARED_LOG_FILE", "shared_pollinate_log.jsonl")
CONTRIBUTION_LOG_DB = os.environ.get("CONTRIBUTION_LOG_DB", "users.db")

# ========== 相似度与积分规则 ==========
# 注意：SIMILARITY_THRESHOLD 是旧版 TF-IDF 使用的阈值
# 新版 knowledge_service 使用 embedding 时会用独立的阈值，不使用这个值
SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", "0.30"))
EXTERNAL_SEED_REWARD = int(os.environ.get("EXTERNAL_SEED_REWARD", "5"))
MANUAL_POLLINATE_BASIC_REWARD = int(os.environ.get("MANUAL_POLLINATE_BASIC_REWARD", "3"))
MANUAL_POLLINATE_EXPERT_REWARD = int(os.environ.get("MANUAL_POLLINATE_EXPERT_REWARD", "10"))
QUERY_DEDUCTION = int(os.environ.get("QUERY_DEDUCTION", "2"))

# ========== 节点与发现 ==========
NODE_ID = os.environ.get("SASES_NODE_ID", "node-001")
NODE_NAME = os.environ.get("SASES_NODE_NAME", "SASES Node")
PEER_NODES = [x.strip() for x in os.environ.get("SASES_PEERS", "").split(",") if x.strip()]

# mDNS 发现
ENABLE_MDNS = os.environ.get("SASES_ENABLE_MDNS", "false").lower() == "true"
MDNS_SERVICE_TYPE = "_sases._tcp.local."

# ========== DashScope Embedding（用于混合模式） ==========
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
DASHSCOPE_EMBEDDING_MODEL = os.environ.get(
    "DASHSCOPE_EMBEDDING_MODEL",
    "text-embedding-v3"
)

# Embedding 模式：local / api / hybrid
EMBEDDING_MODE = os.environ.get("EMBEDDING_MODE", "hybrid")

# 混合模式的边界阈值
HYBRID_LOW_THRESHOLD = float(os.environ.get("HYBRID_LOW_THRESHOLD", "0.35"))
HYBRID_HIGH_THRESHOLD = float(os.environ.get("HYBRID_HIGH_THRESHOLD", "0.88"))

# ========== 指挥官/审核员 LLM 参数 ==========
COMMANDER_MAX_TOKENS = int(os.environ.get("COMMANDER_MAX_TOKENS", "16000"))
REPLAN_MAX_TOKENS = int(os.environ.get("REPLAN_MAX_TOKENS", "16000"))
SUMMARY_MAX_TOKENS = int(os.environ.get("SUMMARY_MAX_TOKENS", "1000"))

# ========== 蜂群模式（防篡改） ==========
# off: 关闭（单用户，默认）
# alert: 只告警（联邦早期，多信任方）
# enforce: 强制（积分挂钩真实价值时）
HIVE_MODE = os.environ.get("SASES_HIVE_MODE", "off").lower().strip()
if HIVE_MODE not in ("off", "alert", "enforce"):
    HIVE_MODE = "off"

HIVE_PEERS = [x.strip() for x in os.environ.get("SASES_HIVE_PEERS", "").split(",") if x.strip()]
HIVE_NODE_ID = os.environ.get("SASES_HIVE_NODE_ID", "")
HIVE_ANCHOR_INTERVAL = int(os.environ.get("SASES_HIVE_ANCHOR_INTERVAL", "3600"))
HIVE_HEARTBEAT_INTERVAL = int(os.environ.get("SASES_HIVE_HEARTBEAT_INTERVAL", "300"))
