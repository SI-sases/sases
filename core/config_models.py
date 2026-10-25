from core.config_models import (
    ModelConfig,
    ProviderConfig,
    StorageConfig,
    CreditConfig,
    SecurityConfig,
    NodeConfig,
    FileSizeConfig,
)

# 实例化各配置组
_model_cfg = ModelConfig()
_provider_cfg = ProviderConfig()
_storage_cfg = StorageConfig()
_credit_cfg = CreditConfig()
_security_cfg = SecurityConfig()
_node_cfg = NodeConfig()
_file_size_cfg = FileSizeConfig()

# 模型配置
DEEPSEEK_API_KEY = _model_cfg.deepseek_api_key
DEEPSEEK_BASE_URL = _model_cfg.deepseek_base_url
MODEL_NAME = _model_cfg.model_name
VISION_MODEL_NAME = _model_cfg.vision_model_name

# 提供商配置
PROVIDER_BASE_URLS = _provider_cfg.base_urls
PROVIDER_ALIASES = _provider_cfg.aliases
VISION_MODEL_BY_PROVIDER = _provider_cfg.vision_models
AUDIO_MODEL_BY_PROVIDER = _provider_cfg.audio_models
VIDEO_MODEL_BY_PROVIDER = _provider_cfg.video_models

# 存储配置
DB_FILE = _storage_cfg.db_file
KB_FILE = _storage_cfg.kb_file
SEED_POOL_FILE = _storage_cfg.seed_pool_file
MAIN_SEED_FILE = _storage_cfg.main_seed_file
SHARED_LOG_FILE = _storage_cfg.shared_log_file
CONTRIBUTION_LOG_DB = _storage_cfg.contribution_log_db

# 积分与相似度配置
SIMILARITY_THRESHOLD = _credit_cfg.similarity_threshold
EXTERNAL_SEED_REWARD = _credit_cfg.external_seed_reward
MANUAL_POLLINATE_BASIC_REWARD = _credit_cfg.manual_pollinate_basic_reward
MANUAL_POLLINATE_EXPERT_REWARD = _credit_cfg.manual_pollinate_expert_reward
QUERY_DEDUCTION = _credit_cfg.query_deduction

# 安全配置
SASES_SECRET_KEY = _security_cfg.sases_secret_key
SIGN_KEY_FILE = _security_cfg.sign_key_file
API_KEY_ENCRYPTION_KEY_FILE = _security_cfg.api_key_encryption_key_file
NODE_TOKEN = _security_cfg.node_token

# 节点与发现配置
NODE_ID = _node_cfg.node_id
NODE_NAME = _node_cfg.node_name
PEER_NODES = _node_cfg.peer_nodes
ENABLE_MDNS = _node_cfg.enable_mdns
MDNS_SERVICE_TYPE = _node_cfg.mdns_service_type
SASES_PORT = _node_cfg.port

# 文件大小限制
MAX_IMAGE_SIZE = _file_size_cfg.max_image_size
MAX_AUDIO_SIZE = _file_size_cfg.max_audio_size
MAX_VIDEO_SIZE = _file_size_cfg.max_video_size
