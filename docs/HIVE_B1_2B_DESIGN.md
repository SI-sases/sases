# B1.2-B 设计文档：读写副本（写代理模式）

## 背景

B1.2-A 已实现：
- 8001 主节点（可读写）
- 8002/8003 副本（只读，独立 DB，定期从 8001 同步）

用户在副本访问时，写操作被 403 拦截。

## 目标

让用户在 8002/8003 也能正常写入，且数据最终一致。

## 非目标

- 不做"多主同时写"（B2 阶段）
- 不做冲突解决（B2 阶段）
- 不做 BFT 共识（B3 阶段）

## 核心设计：写代理

用户 → 副本（8002）→ 主节点（8001）→ replica sync 回流 → 副本更新

**关键**：副本不真正写数据，而是"代理"到主节点。用户无感。

## 方案对比

| 方案 | 冲突 | 复杂度 | 用户感知 |
|------|------|--------|---------|
| 多主同时写 | 复杂 | 高 | 快 |
| **写代理** | **无** | **中** | **稍慢但可接受** |
| 只读副本 | 无 | 低 | 差（不能写）|

## P0 安全与可靠性要求（必须做）

### 1. 节点级认证

转发请求带 Ed25519 签名，主节点验证节点身份：
- 用户 JWT（证明"用户 A 授权"）
- 节点签名（证明"请求来自合法节点 8002"）
- 8002 在 node_registry 里状态为 active

复用 B.1 的 identity.py 和 B.2 的 node_registry。

### 2. 幂等性

转发请求带 request_id（UUID），主节点去重：

```sql
CREATE TABLE IF NOT EXISTS forwarded_requests (
    request_id TEXT PRIMARY KEY,
    node_id TEXT,
    result_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

收到请求先查 request_id，存在则返回上次结果。

### 3. 死循环防护

转发请求带 `X-Hive-Forwarded: true` header，已转发的拒绝再次转发（返回 508）。

只转发给 role=master 的节点。

### 4. 回滚开关

```
HIVE_FORWARD_MODE=auto   # 副本自动转发（B1.2-B 默认）
HIVE_FORWARD_MODE=reject # 副本返回 403（B1.2-A 行为）
```

出问题时可快速回退，不需要改代码。


## P1 可靠性要求

### 5. 主节点故障切换

从 node_registry 查所有 role=master 且 status=active 的节点，按顺序尝试。

```
8002 → 8001 失败
   ↓ 重试 2 次
8002 → node-B（也是副本，跳过）
8002 → node-C（也是副本，跳过）
   ↓
返回 503
```

### 6. 转发 body 大小

用流式转发（httpx stream 模式），不要缓冲整个 body。

### 7. 时间戳一致性

统一由 8001 生成 created_at。副本转发时不带时间戳，8001 用自己的时钟。

### 8. 监控

/hive/status 增加字段：

```json
{
    "forward_mode": "auto",
    "forward_stats": {
        "total": 1234,
        "success": 1230,
        "failed": 4,
        "avg_latency_ms": 145
    }
}
```

## P2 增强（可选）

### 9. WebSocket 跨节点推送

8002 订阅 8001 的 /ws/hive/broadcast，收到事件后转发给本地 WS 客户端。

如果不做，用户需手动刷新才能看到别人发的消息。

### 10. 用户感知设计

本地 localStorage 缓存"我刚发的消息"，30 秒内显示"同步中"，之后正常显示。

## 分阶段实施

### 阶段 1：写代理基础（1-2 天）

- 副本中间件改为"转发"而非"403"
- 只支持 POST /messages/send
- 只转发给 8001
- 加 P0 四项（认证+幂等+防循环+回滚开关）

验证：用户在 8002 发消息，8001 出现该消息，30 秒后 8002 也能看到。

