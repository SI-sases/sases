# SASES 故障转移设计文档

版本：v1.0（2026-10-11）
状态：已完成

## 一、目标

当主节点（8001）挂掉时，副本节点（8002/8003）能自动选举新主，接管写入，并同步数据。

## 二、核心机制

### 1. 健康检测

- 从节点每 10 秒 GET 主节点 /hive/health
- 连续失败 → 触发选举

### 2. 选举协议

- 向 HIVE_PEERS 广播 /hive/election/vote
- 请求带 Ed25519 签名
- 优先级小的胜（node-A=10 > node-B=20 > node-C=30）
- 获得多数票（2/3）当选
- epoch 号防裂脑

### 3. 当选后行为

- set_my_role("master")
- save_epoch_to_db(new_epoch)
- 清空 HIVE_MASTERS（自己是主）
- 中间件切换：本地处理写请求（不再转发）

### 4. 原主恢复

- 启动时 load_epoch_from_db()
- check_higher_epoch_on_startup()（查本地 registry）
- check_peer_epochs()（HTTP 查 peers 的 epoch）
- 发现更高 epoch 的 master → 自动降级为 slave

### 5. 数据同步

- 降级后从新主同步（REPLICA_MODE=true）
- 同步范围：REPLICA_TABLES（users / conversations / messages / groups / ...）

## 三、文件结构

| 文件 | 职责 |
|------|------|
| core/node/election.py | 选举 + 健康检测 + 降级 |
| core/node/heartbeat.py | 心跳对比（账本一致） |
| core/node/forwarder.py | 写代理转发 |
| core/ledger/replica.py | 副本同步 |
| core/hive/api.py | /hive/election/* 端点 |
| core/hive/service.py | 挂载后台任务 |
| core/bootstrap.py | 中间件角色判断 |

## 四、环境变量

### 主节点

set SASES_PORT=8001
set SASES_NODE_ID=node-A
set HIVE_PEERS=http://127.0.0.1:8002,http://127.0.0.1:8003

### 从节点（初始指向 8001）

set SASES_PORT=8002
set SASES_NODE_ID=node-B
set HIVE_ROLE=slave
set HIVE_MASTERS=http://127.0.0.1:8001
set HIVE_PEERS=http://127.0.0.1:8003
set REPLICA_MODE=true
set HIVE_FORWARD_MODE=auto
set SASES_DB_PATH=hive-nodes/node-B/replica.db
set SASES_DISABLE_FK=true

## 五、测试方法

### 场景：主节点挂掉

1. 启动 8001（master）+ 8002 + 8003（slave）
2. 从 8002 POST /messages/send → 200（转发）
3. 停掉 8001（Ctrl+C）
4. 等 60 秒
5. 观察 8002 日志：WON: epoch=1
6. 观察 8003 日志：LOST: votes=1/2
7. 从 8002 POST /messages/send → 200（本地）

### 场景：主节点恢复

1. 重启 8001（带 HIVE_PEERS）
2. 观察 8001 日志：startup: peer ... is master (epoch=1), downgrading to slave
3. 观察 8001 日志：[replica] synced N rows
4. 8001 数据与 8002 一致

## 六、已知限制

| # | 限制 | 影响 |
|---|------|------|
| 1 | 数据同步是「全量覆盖」（DELETE+INSERT）| 生产需改为合并 |
| 2 | 选举依赖 HIVE_PEERS 环境变量 | 需手动配置 |
| 3 | 无心跳超时阈值自适应 | 固定 10 秒 |
| 4 | 无网络分区容忍（仅主挂场景）| 复杂分区需 B3 |

## 七、版本历史

| 版本 | 内容 |
|------|------|
| v0.27.0 | 故障转移完整闭环 |
| v0.27.1 | 修复 register_routes 日志 |

## 八、一句话总结

三层验证：选举（签名+优先级）→ 当选（epoch+本地处理）→ 恢复（检测+降级+同步）。
