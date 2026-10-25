# 蜂巢 A 阶段遗留补充（2026-10-08）

## 目标

在 A 阶段多主镜像基础上，补齐三项生产必备能力。

## 三项补充

### 1. 节点认证（HIVE_TOKEN）

- config.py 加 HIVE_TOKEN 环境变量
- api.py 加 _check_hive_token 依赖（token 为空时放行）
- client.py 新建 hive_headers() helper
- sync.py / heartbeat.py / majority.py 所有出站请求带 header

### 2. 降级告警

- config.py 加 DEGRADE_THRESHOLD（默认 3）
- sync.py 加 _health 状态追踪：last_sync_at / last_sync_ok / consecutive_failures / degraded
- 每次同步成功调用 _mark_sync_ok()，失败调用 _mark_sync_fail()
- 连续失败达到阈值 → 打印 DEGRADED，恢复时打印 HEALTH RECOVERED

### 3. /hive/status 端点

返回当前节点的角色、同步健康状态、最新锚定信息。

## 环境变量

```
HIVE_TOKEN=              # 空则不校验
HIVE_DEGRADE_THRESHOLD=3 # 连续失败阈值
```

## 验证结果

| 测试 | 结果 |
|------|------|
| 12 节点 hash 一致 | ✅ 2a876578... count=116 |
| /hive/status 返回 | ✅ role=slave, sync.last_sync_ok=true |
| degraded 状态 | ✅ false |
| consecutive_failures | ✅ 0 |

## 关键设计

- **默认不启用认证**：HIVE_TOKEN 为空时所有请求放行，向后兼容
- **同步健康状态内存存储**：不落库，重启后重置（生产可改为落库）
- **降级只告警不阻断**：DEGRADED 状态仍继续尝试同步

## 后续（B 阶段前置）

- 幂等性：当前用 DELETE+INSERT 全量覆盖，因从节点轮询只命中一个 master 所以安全
- B 阶段引入双向同步时需改为 INSERT OR REPLACE + logical_clock

## 相关文件

- core/hive/config.py
- core/hive/api.py
- core/hive/client.py（新建）
- core/hive/sync.py
- core/hive/heartbeat.py
- core/hive/majority.py
