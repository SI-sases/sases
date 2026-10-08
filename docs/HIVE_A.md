# 蜂巢 A 阶段：多主镜像（2026-10-08）

## 目标

在 P1 基础上，把 1 主 + 9 从升级为 3 主 + 9 从，去掉主节点单点。

## 架构

master（8001，完整 SASES，权威账本）
   ↓ 单向同步
master（8002，轻量，只跑 hive）  ← 镜像
master（8003，轻量，只跑 hive）  ← 镜像
   ↓ 从节点可从三者任一同步
slave × 9（9001-9009）

## 核心能力

- 任意 1 个主节点挂掉，从节点自动切换到其他主节点
- 3 主之间 hash 保持实时一致
- 恢复后自动追平

## 关键改动

| 文件 | 改动 |
|------|------|
| core/hive/config.py | 加 HIVE_MASTERS（列表，逗号分隔） |
| core/hive/sync.py | sync 改成轮询 HIVE_MASTERS |
| core/hive/standalone_master.py | 新建，轻量主节点入口 |
| core/hive/ledger.py | contribution_log 加 event_type 字段 |
| scripts/hive/start_masters.py | 新建，启动 8002/8003 |
| scripts/hive/check_masters.py | 新建，检查主节点状态 |
| scripts/hive/reset_masters.py | 新建，重置主节点 DB |
| scripts/hive_batch.py | 传 HIVE_MASTERS 而非 HIVE_MASTER |

## 环境变量

主节点：
```
ENABLE_HIVE=true
HIVE_ROLE=master
```

从节点：
```
ENABLE_HIVE=true
HIVE_ROLE=slave
HIVE_MASTERS=http://127.0.0.1:8001,http://127.0.0.1:8002,http://127.0.0.1:8003
SASES_DISABLE_FK=true
```

轻量主节点：
```
HIVE_ROLE=master
HIVE_AUTHORITY=http://127.0.0.1:8001
SASES_DISABLE_FK=true
```

## 启动顺序

```
# 1. 启动主 SASES（8001）
python -m uvicorn app_full:app --port 8001

# 2. 启动 2 轻量主节点
python scripts/hive/start_masters.py

# 3. 启动 9 从节点
python scripts/hive_batch.py --count 9 --port-base 9001
```

## 验证结果

| 测试 | 结果 |
|------|------|
| 3 主 hash 一致 | ✅ 857256b4... count=113 |
| 9 从 hash 一致 | ✅ |
| 停 8001 | ✅ 从节点保持同步 |
| 恢复 8001 | ✅ 自动追平 |

## B 阶段预留（已就绪）

- logical_clock 字段（待加）
- ledger_versions 表（待加）
- /hive/ledger/since/{version} 增量接口（待加）
- conflict.py 冲突解决（待加）
- SYNC_MODE 参数（待加）

## 遗留

- 节点认证（HIVE_TOKEN）未加——同机部署可接受，跨机器前必须加
- 同步幂等性（INSERT OR REPLACE）—— 目前用 DELETE+INSERT，3 主同时推有风险
- 从节点降级告警——主节点全挂时没有显式告警
