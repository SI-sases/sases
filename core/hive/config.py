"""core/hive/config.py —— 蜂巢配置（环境变量驱动）。

角色说明：
  master  —— 主节点，有完整业务数据，对外提供账本
  slave   —— 从节点，只同步 + 锚定（阶段 1 使用）
  peer    —— 对等节点，双向同步（阶段 3 使用）
"""
import os

ENABLE_HIVE = os.environ.get("ENABLE_HIVE", "false").lower() in ("1", "true", "yes")
HIVE_ROLE = os.environ.get("HIVE_ROLE", "master").lower()
NODE_ID = os.environ.get("SASES_NODE_ID", "node-A")

# 主节点地址（slave 用）
HIVE_MASTER = os.environ.get("HIVE_MASTER", "").rstrip("/")

# 对等节点列表（peer 用；master 也可以配置用于未来互证）
HIVE_PEERS = [
    p.strip().rstrip("/")
    for p in os.environ.get("HIVE_PEERS", "").split(",")
    if p.strip()
]

# 运行模式：off 只跑锚定 / alert 告警 / enforce 锁定
HIVE_MODE = os.environ.get("HIVE_MODE", "alert").lower()

# 各任务周期（秒）
ANCHOR_INTERVAL = int(os.environ.get("HIVE_ANCHOR_INTERVAL", "3600"))
HEARTBEAT_INTERVAL = int(os.environ.get("HIVE_HEARTBEAT_INTERVAL", "15"))
VOTE_INTERVAL = int(os.environ.get("HIVE_VOTE_INTERVAL", "20"))
SYNC_INTERVAL = int(os.environ.get("HIVE_SYNC_INTERVAL", "30"))