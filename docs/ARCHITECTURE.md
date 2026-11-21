# SASES 架构总览（当前执行链）

版本：2026-11-22
状态：DSH 对齐后的执行架构

## 一、入口

| 入口 | 代码 | 执行 |
|---|---|---|
| 普通聊天（流式） | `services/chat_stream.py` | BASE + `agent_messages` + LLM |
| 任务/前缀消息 | `services/message/send.py` | `agent_loop` |
| A2A 确认 | `api_routes/supervisor_routes.py` → `execution_gateway` | `agent_loop(strict)` |
| 定时任务 | `services/scheduled_task_service.py` → `execution_gateway` | `agent_loop(strict)` |
| 群 @聊天 | `services/group_agent_service.py` | `agent_loop(fast, 无工具)` |
| 群 @执行 | 同上，`执行：` 前缀 | `agent_loop(strict, 有工具)` |

## 二、执行循环

```
agent_loop.run
  ├─ agent_compact.maybe_compact        （token 压力）
  ├─ tool_pruner.prune_messages         （8k 工具裁剪，仅请求）
  ├─ agent_context.build_runtime_context（可选，尾部注入）
  ├─ LLM(tools=固定 schema)
  ├─ tool_gateway.invoke_tool_async
  ├─ 审批 / 检查点 / 幂等
  └─ memory/project 写回（可选）
```

关键文件：

| 文件 | 职责 |
|---|---|
| `services/agent_loop.py` | 单循环、工具调用、严格审核 |
| `services/agent_memory.py` | append-only 日志 + summary 读取 |
| `services/agent_compact.py` | token 压力压缩 |
| `services/tool_pruner.py` | 工具结果裁剪 |
| `services/token_meter.py` | 确定性 token 估算 |
| `services/agent_context.py` | 运行时上下文 provider |
| `services/execution_gateway.py` | A2A/定时统一入口 |
| `tool_gateway.py` | 工具路由（本地/HTTP/扩展） |

## 三、会话数据

| 表 | 用途 |
|---|---|
| `messages` | UI 消息 |
| `agent_messages` | LLM append-only 日志（含 tool） |
| `agent_summary` | 压缩摘要 + `summary_message_id` |
| `agent_questions` | ask_user |
| `agent_pending_tools` | 审批挂起工具 |
| `run_steps` / `run_trace` / `run_artifacts` | 执行轨迹/产物 |
| `approvals` | 审批 |
| `file_checkpoints` | 文件回滚 |
| `tool_usage_daily` | 工具使用统计 |

## 四、上下文策略

```
system: BASE_SYSTEM（静态）
history: agent_messages（compacted=0）
summary: agent_summary（替换事件）
runtime: 可选尾部 user 消息（不落库）
user: 本轮输入
tools: 固定顺序
```

压缩：

- 触发 `min(W*0.8, W-O-B)`
- 保留最近 16%
- 摘要请求复用 system + tools + 旧历史
- 旧消息 `compacted=1`，新增 assistant 摘要
- 默认窗口 131072 / 输出 4096 / headroom 32768

工具裁剪：

- `>8192` → head 4096 + marker + tail 1024
- 完整内容仍在 `agent_messages`

## 五、群 / 好友

### 好友 A2A

- `cross_account_delivery.py`
- 双方自由 + 任务意图 → `create_proposed_run`
- 确认 → `execution_gateway.run_a2a`
- 结果脱敏后回传
- 拒绝/超时回执

### 群聊

- `group_service.py`：群、成员、任务、红包、积分
- `group_agent_service.py`：群 @ → `agent_loop`
- 群会话 key：`-group_id`（`agent_messages`）
- 结果写回 `group_messages` 并广播

## 六、节点层

保留：

```
core/node/       节点身份/注册/转发/心跳
core/ledger/     账本/同步
core/broadcast/  WS 广播
core/hive/       入口 shim
```

## 七、开关

| 开关 | 默认 |
|---|---|
| `SASES_AGENT_LOOP` | 1（0 回退旧路径） |
| `SASES_TOOL_PRUNER` | 1 |
| `SASES_TOKEN_COMPACT` | 1 |
| `SASES_RUNTIME_CONTEXT` | 0 |
| `SASES_RUNTIME_RECALL` | 0 |
| `SASES_MEMORY_WRITE` | 0 |
| `SASES_REQUIRE_APPROVAL` | 0 |

## 八、测试

- `tests/ui/`：UI 快照
- 手工回归：聊天 / A2A / 定时 / 群 / 红包 / 任务
- 长上下文：20 轮 + 自动压缩
- 30 轮短会话：缓存 96.96%

## 九、文档

当前只保留：

- `SASES.md`（项目约束）
- `docs/STATUS_AND_PLAN_20261122.md`（状态/计划）
- `docs/ARCHITECTURE.md`（本文件）
- `docs/DSH_CONTEXT_IMPLEMENTATION.md`（上下文实现）
- `docs/API_INDEX.md` / `DATABASE.md`（生成索引）

旧总结在 `docs/history/`，只作考古，不作为执行上下文。
