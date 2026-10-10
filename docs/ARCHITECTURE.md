# SASES 架构总览

版本：v0.26.4（2026-10-10）
状态：整合第 3 批完成

## 一、三层结构

```
core/
├── node/         节点基础设施（身份、注册、转发、心跳、多数决）
├── ledger/       账本（锚定、副本、同步）
├── broadcast/    广播（WS 连接池 + 广播接口）
├── hive/         入口壳（挂载上述模块，提供 HTTP 端点）
├── swarm/        蜂巢资源层（未来：算力、存储、模型）
├── services/     业务逻辑（用户、消息、群、宠物...）
├── api_routes/   HTTP 路由层
└── db.py         数据库初始化
```

## 二、模块职责

### core/node/ —— 节点基础设施

| 文件 | 职责 |
|------|------|
| identity.py | Ed25519 密钥对，签名/验签 |
| registry.py | 节点注册表（node_id + public_key + url + role） |
| register_client.py | 向 peers 注册自己 |
| client.py | 出站 HTTP 请求 header（含 HIVE_TOKEN） |
| heartbeat.py | 心跳对比 + 告警去重 |
| majority.py | 多数决（2/3 一致为准） |
| forwarder.py | 写代理转发（含熔断、幂等、防循环） |

### core/ledger/ —— 账本

| 文件 | 职责 |
|------|------|
| ledger.py | 账本 hash 计算（锚定用：groups + group_messages） |
| anchor.py | 定期写 credit_anchors |
| replica.py | 副本同步（从主节点拉核心业务表） |
| sync.py | 全量同步（兼容旧接口） |

### core/broadcast/ —— 广播

| 文件 | 职责 |
|------|------|
| ws_hub.py | WS 连接池（group/user），纯 Python，无 FastAPI 依赖 |
| __init__.py | 导出 broadcast_to_user / broadcast_to_group |

**关键**：未来 L2（节点间广播）在 ws_hub 基础上扩展。

### core/hive/ —— 入口壳

| 文件 | 职责 |
|------|------|
| config.py | 配置读取（env + config.json + 默认值） |
| api.py | HTTP 端点（/hive/hash、/hive/anchor、/hive/register...） |
| service.py | 挂载路由 + 后台任务 |
| standalone.py | 轻量从节点入口 |
| standalone_master.py | 轻量主节点入口 |

### core/swarm/ —— 蜂巢资源层（未来）

预留：算力共享、存储分片、模型托管。

## 三、依赖方向

```
api_routes/services
        ↓
    core/hive/
        ↓
  ┌─────┴─────┐
  ↓           ↓
core/node/  core/ledger/
  ↓           ↓
  └─────┬─────┘
        ↓
  core/broadcast/
        ↓
      core/db.py
```

依赖规则：
- 上层可以依赖下层
- 同层可以互相依赖
- 下层不依赖上层

## 四、数据流

### 用户请求（读）

```
浏览器 → api_routes → services → db
```

### 用户请求（写）

```
浏览器 → api_routes → services（本地写）
  或
浏览器 → api_routes → forwarder → 主节点 → services（本地写）
```

### 节点间同步

```
主节点 → replica.export_replica() → 从节点
从节点 → sync_from_master() → 本地 replica.db
```

### 广播

```
services → broadcast.ws_hub → 本地 WS 客户端
```

## 五、向后兼容

`core/hive/*.py` 保留为 shim，指向新位置：

- core/hive/identity.py → core/node/identity.py
- core/hive/registry.py → core/node/registry.py
- core/hive/ledger.py → core/ledger/ledger.py
- core/hive/client.py → core/node/client.py
- core/hive/heartbeat.py → core/node/heartbeat.py
- core/hive/majority.py → core/node/majority.py
- core/hive/register_client.py → core/node/register_client.py
- core/hive/forwarder.py → core/node/forwarder.py
- core/hive/anchor.py → core/ledger/anchor.py
- core/hive/replica.py → core/ledger/replica.py
- core/hive/sync.py → core/ledger/sync.py

**待清理**：确认无引用后删除 shim。

## 六、未来扩展

### L2 节点间广播（上服务器前）

在 `core/broadcast/` 加 `node.py`，通过 WS 长连接在主节点和副本间转发广播。

### 蜂巢资源层（蜂巢计划）

在 `core/swarm/` 下新增：
- compute.py（算力共享）
- storage.py（存储分片）
- model.py（模型托管）

### B3 真去中心（长期）

- DHT 节点发现
- 共识算法
- E2E 加密

## 七、版本历史

| 版本 | 内容 |
|------|------|
| v0.26.0 | 整合前冻结 |
| v0.26.1 | 第 1 批：建目录 + 迁移 3 文件 |
| v0.26.2 | 第 2 批：迁移 7 文件 |
| v0.26.3 | 第 3 批 A：迁移 forwarder.py |
| v0.26.4 | 第 3 批 B：抽出 broadcast 模块 |

## 八、一句话

三层平行：node（节点）+ ledger（账本）+ broadcast（广播），
通过 hive（入口）挂载，swarm（资源）预留。

整合原则：
- 目录分层，不重写逻辑
- shim 兼容，调用方零改动
- 可撤除，任一层可独立关闭
