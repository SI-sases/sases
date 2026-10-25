# 蜂巢 P1：主从同步 + 锚定（2026-10-07）

## 目标

在 SASES 上落地"官方信任节点群"，先做 1 主 + 9 从的单向同步。

## 架构

master（8001）  — 完整 SASES + 官方账本
   ↓ 单向同步
slave × 9（9001-9009） — 只跑 hive 模块 + 账本副本

## 核心机制

### 1. 账本快照（core/hive/ledger.py）
只扫"官方账本"表，不扫用户私有数据：
- transactions（id, sender_id, receiver_id, amount, tx_type, status）
- contribution_log（id, user_id, points）
- groups（id, name, owner_id）
- group_messages（id, group_id, sender_id, content）

### 2. 锚定（core/hive/anchor.py）
每小时写一次 hash 到 credit_anchors。

### 3. 同步（core/hive/sync.py）
slave 每 30 秒从 master 拉全量账本，覆盖本地。

### 4. 心跳对比（core/hive/heartbeat.py）
每 60 秒拉 peers 的 /hive/anchor，对比 hash。不一致则告警（带去重）。

### 5. 多数决（core/hive/majority.py）
每 120 秒收集所有节点 hash，2/3 一致则多数为真，少数标记 SUSPECT。

## 关键决策

| 决策 | 理由 |
|------|------|
| 用 connect 判端口占用（不是 bind） | 避开 Windows SO_REUSEADDR 陷阱 |
| 从节点关闭外键约束（SASES_DISABLE_FK） | 从节点无用户数据，FK 无意义 |
| 从节点用独立 DB（hive-nodes/node-XX/hive.db） | 与主 DB 隔离 |
| 心跳/锚定周期可环境变量覆盖 | 生产用大值，调试用小值 |

## 已删除

- core/services/anchor_service.py（被 core/hive/ledger + anchor 取代）
- bootstrap.py 里旧的 periodic_anchor_task

## 验证结果

| 测试 | 结果 |
|------|------|
| 9 从节点启动 | ✅ |
| 同步后 10 节点 hash 一致 | ✅ a4796e09... |
| 篡改 node-01 | ✅ hash 立即变 b808b5f3... |
| 30 秒后自动恢复 | ✅ hash 回到 a4796e09... |
| 主节点日志无 MISMATCH | ✅（系统健康）|

## 阶段 2 待做

- 3-5 主节点互备（去掉单点）
- 双向同步
- Ed25519 节点身份
- 告警→锁定（enforce 模式）

## 用法

主节点（在主 SASES 的 .env）：
```
ENABLE_HIVE=true
HIVE_ROLE=master
```

从节点（批量）：
```
python scripts/hive_batch.py --count 9 --port-base 9001 --master http://127.0.0.1:8001
```

## 相关文件

- core/hive/ —— 新模块（11 文件）
- core/db.py —— SASES_DB_PATH / SASES_DISABLE_FK / credit_anchors / origin_node
- core/config.py —— NODE_ID
- scripts/hive_batch.py —— 重写
