"""core/profile.py —— 节点配置档（区分官方节点 / 用户设备）。

环境变量：
  SASES_PROFILE=official  （默认）官方节点
  SASES_PROFILE=personal  用户设备

特性开关：
  ENABLE_ELECTION     是否参与官方选举
  ENABLE_L2_BROADCAST 是否启用节点间广播
  ENABLE_HIDDEN_NODES 是否启动隐藏节点
  ACCEPT_EXTERNAL     是否接受外部连接
"""
import os

PROFILE = os.environ.get("SASES_PROFILE", "official").lower()
IS_OFFICIAL = PROFILE == "official"
IS_PERSONAL = PROFILE == "personal"

# 特性开关
ENABLE_ELECTION = IS_OFFICIAL
ENABLE_L2_BROADCAST = True  # 两种 profile 都启用（用户设备也需要同步）
ENABLE_HIDDEN_NODES = IS_PERSONAL
ACCEPT_EXTERNAL = IS_OFFICIAL


def info():
    return {
        "profile": PROFILE,
        "is_official": IS_OFFICIAL,
        "is_personal": IS_PERSONAL,
        "enable_election": ENABLE_ELECTION,
        "enable_l2_broadcast": ENABLE_L2_BROADCAST,
        "enable_hidden_nodes": ENABLE_HIDDEN_NODES,
        "accept_external": ACCEPT_EXTERNAL,
    }