# SASES 上下文 / 压缩 / 记忆 / 项目库 · 对齐 DSH 详细方案

> 参考：DSH 安装包 `dsh-compaction-basic`、`dsh-compaction-tool-result-pruner`、`dsh-token-meter`、`dsh-system-prompt`、`dsh-session-*`。
> 原则：**DSH 的机制 + SASES 的现有数据，不推翻前端和已有表。**

---

## 0. 目标

| 指标 | 目标 |
|---|---|
| 30 轮会话 | 不爆上下文 |
| 压缩后缓存命中 | ≥90% |
| 工具结果 | 单条 ≤8k 字符进模型 |
| 摘要 token | ≤被替换历史的 30% |
| 普通聊天 | 不注入记忆/项目库 |
| 任务类 | 最多 3 条记忆 + 3 个项目片段 |

---

## 1. DSH 关键机制（已核对）

### 1.1 压缩

- 触发：
  ```text
  threshold = floor(min(W × 0.8, W − O − headroom))
  ```
  `W` 上下文窗口，`O` 输出预留，`headroom` 默认 65536。
- 保留：最近 `16% × (W − O)` 原文。
- 摘要：替换最老一段，只留一条 summary message。
- 溢出：确认 overflow 后压缩一次并重试。
- 摘要请求：**复用 system + tools + 被替换历史的前缀**，只在尾部加“请总结”。

### 1.2 工具裁剪

- 只在压缩触发后运行。
- 默认：`>8192` 字符 → head `4096` + `...[middle pruned]...` + tail `1024`。
- 无模型调用；完整原文仍在 session log。

### 1.3 Token 计量

- 重放日志、确定性估算、无模型调用。
- 提供 `totalTokens / surfaceTokens / contextBreakdown`。
- 压缩、UI 占用、遥测共用一套数字。

### 1.4 系统提示

- 有序 sections + runtime context。
- 动态事实只在变化时注入。
- 工具 schema 顺序固定。

### 1.5 记忆

DSH **没有独立记忆包**：

- skills（文件系统）
- 项目指令 / AGENTS.md
- session log

所以 SASES 的向量记忆/项目库不是“照搬”，而是 **可选 provider**。

---

## 2. SASES 现状与差距

| 模块 | 现状 | 差距 |
|---|---|---|
| `agent_compact.py` | 40 条 / 保留 20 条 | 条数驱动，不是 token |
| `unified_context.maybe_compact` | 第二套压缩 | 重复实现 |
| `agent_memory.history` | summary 作为 user 消息前置 | 不是“替换旧段” |
| 工具结果 | `_spill_large` >20k 落 artifact | 20k 仍太大，无 8k pruner |
| `agent_loop` | 只用 BASE + agent_messages | 绕过 memory/project/context |
| `memory_service` | 向量 recall | 新 loop 不调用 |
| `project_service` | 项目库检索 | 新 loop 不调用 |
| token | 字符估算 | 无统一 meter |

**最大问题：新 loop 和旧上下文服务是两个世界。**

---

## 3. 目标架构

```text
agent_loop.run
  ├─ token_meter.measure(history, system, tools)
  ├─ if pressure > threshold:
  │    ├─ tool_pruner.prune(history)
  │    └─ if still pressure: compactor.compact(session)
  ├─ runtime_context.build(...)        ← 只放尾部，不写日志
  ├─ llm(messages = system + history + runtime + user)
  └─ after run: memory/project write
```

### 3.1 数据流

```text
system: BASE_SYSTEM（静态）
history: agent_messages（append-only）
summary: agent_summary（替换事件）
runtime: 本轮临时 user 消息（不落 agent_messages）
user: 本轮输入
tools: 固定 schema 顺序
```

---

## 4. 模块设计

### 4.1 `core/services/token_meter.py`（新增）

```python
def measure(messages, system_prompt, tools, model_window, output_cap):
    # 返回 total/surface/system/tools/messages
```

估算：

```text
ASCII: len // 4
CJK:   cjk_count // 1.5
每消息 +4 token，每工具 +30 token
```

校准：

- 用 `llm_usage.prompt_tokens` 与实际字符比，按 model 存 `calibration`。
- 默认 1.0，允许配置 `SASES_TOKEN_CALIBRATION`。

### 4.2 `core/services/tool_pruner.py`（新增）

```python
def prune(messages, threshold=8192, head=4096, tail=1024):
    # 只改 tool role 的 content
    # 返回 (new_messages, pruned_count, freed_tokens)
```

- 完整结果仍在 `run_artifacts` / `run_trace`
- 不写回 `agent_messages`（只影响本轮请求）
- 记录 `pruned=true` 到 trace

### 4.3 `agent_compact.py` 重写

#### 触发

```python
W = model_window or 131072
O = output_cap or 4096
B = headroom or 32768
threshold = min(W * 0.8, W - O - B)
retain = (W - O) * 0.16
```

#### 选择范围

- 从 system 之后开始
- 保留最近 `retain` tokens
- 不切断 assistant tool_calls + tool result 对
- 至少替换 10 条消息

#### 摘要请求

```python
summary_messages = [
    system,
    *shadowed_history,          # 原样
    {"role": "user", "content": "请总结以上历史，保留目标/文件/失败/未决问题。不要调用工具。"}
]
client.chat.completions.create(
    messages=summary_messages,
    tools=stable_tools,
    tool_choice="none",
    max_tokens=800,
)
```

- 复用完整前缀，提高缓存
- `tool_choice="none"` 防止摘要阶段调工具

#### 写回

`agent_summary` 增加：

```sql
summary_message_id INTEGER
tokens_before INTEGER
tokens_after INTEGER
reason TEXT
```

`agent_messages` 增加：

```sql
compacted INTEGER DEFAULT 0
```

流程：

1. 旧段消息 `compacted=1`
2. 插入一条 `role='assistant', content='【历史摘要】...'`
3. `agent_summary` 记录 `covered_until_id` + `summary_message_id`
4. loader 只取 summary + `compacted=0`

#### loader

```python
[sys] + [summary assistant] + uncompacted messages
```

不再把 summary 当 user 消息拼在最前。

### 4.4 `core/services/agent_context.py`（新增）

```python
def build_runtime_context(user_id, conversation_id, goal, mode):
    # 返回 str 或 ""
```

内容：

```text
【运行时上下文】
- 当前任务：...
- 相关记忆：1) ... 2) ...
- 项目片段：1) ...
```

规则：

- 普通聊天：不注入 memory/project
- 任务类：memory ≤3，project ≤3，每块 ≤600 字
- 任务状态只在变化时注入
- **不写 agent_messages**，只拼进本轮请求尾部
- 总预算 1200 tokens

### 4.5 记忆 / 项目库

保留，但改为 provider：

写入：

- `execution_gateway._finish` 后：
  - `memory_service.remember(task_result)`
  - `project_service.import_execution_note`
- 去重：hash + 相似度
- 失败/成功分开存

读取：

- 只有 `mode in ("task","strict")` 或意图为 task
- `recall(top_k=3)` + `retrieve_project_chunks(top_k=3)`
- 不命中就不注入

### 4.6 系统提示

- `BASE_SYSTEM` 保持静态
- `SASES.md` 只读前缀
- 动态内容只放 `agent_context` 尾部
- 工具 schema 已按 module_id 排序，保持

---

## 5. 执行流程（伪代码）

```python
async def run(...):
    history = agent_memory.history(conversation_id)
    system = BASE_SYSTEM
    tools = stable_tool_schemas(allowed)

    pressure = token_meter.measure(history, system, tools)
    if pressure > threshold:
        history, pruned = tool_pruner.prune(history)
        pressure = token_meter.measure(history, system, tools)
        if pressure > threshold:
            await compactor.compact(conversation_id, history)

    history = agent_memory.history(conversation_id)
    runtime = agent_context.build_runtime_context(user_id, conversation_id, goal, mode)
    messages = [system] + history
    if runtime:
        messages.append({"role": "user", "content": runtime})
    messages.append({"role": "user", "content": goal})

    resp = llm(messages, tools)
```

注意：

- `runtime` 不写库
- 压缩/裁剪只改请求，不删日志
- 旧段通过 `compacted=1` 过滤

---

## 6. 迁移

### 6.1 表变更（migration v10）

```sql
ALTER TABLE agent_summary ADD COLUMN summary_message_id INTEGER;
ALTER TABLE agent_summary ADD COLUMN tokens_before INTEGER;
ALTER TABLE agent_summary ADD COLUMN tokens_after INTEGER;
ALTER TABLE agent_summary ADD COLUMN reason TEXT;
ALTER TABLE agent_messages ADD COLUMN compacted INTEGER DEFAULT 0;
```

### 6.2 兼容

- 旧 summary（user 消息）继续可读
- 新 loader 优先 `summary_message_id`
- 没有新字段时退回旧逻辑

---

## 7. 开关

| 开关 | 默认 | 作用 |
|---|---|---|
| `SASES_TOKEN_COMPACT` | 0 | 新 token 压缩 |
| `SASES_TOOL_PRUNER` | 0 | 8k 裁剪 |
| `SASES_RUNTIME_CONTEXT` | 0 | 记忆/项目注入 |

灰度：

```text
先 pruner → 再 compact → 再 runtime context
```

---

## 8. 验收

| 项 | 方法 | 目标 |
|---|---|---|
| 30 轮不爆 | 连续 task | 无 overflow |
| 缓存 | `/stats/llm-usage` | ≥90% |
| 摘要成本 | 对比 tokens | ≤30% |
| 工具裁剪 | 大 grep | ≤8k 字符 |
| 普通聊天 | 检查 prompt | 无记忆/项目 |
| 任务 | 检查 prompt | ≤3 + 3 |
| 回滚 | 关开关 | 行为恢复 |

---

## 9. 分阶段

| 阶段 | 内容 | 工期 |
|---|---|---|
| M0 | token_meter + 日志（不改行为） | 1 天 |
| M1 | tool_pruner | 1 天 |
| M2 | compact 重写 + v10 | 2–3 天 |
| M3 | runtime_context | 2 天 |
| M4 | memory/project provider | 3–5 天 |
| M5 | 文档收敛 / 30 轮压测 | 1 天 |

---

## 10. 旧文档处理

- 全部移到 `docs/history/`
- 只保留：
  - `SASES.md`
  - `docs/STATUS_AND_PLAN_20261122.md`
  - `docs/ARCHITECTURE.md`（更新）
- 旧总结不再作为执行上下文

---

## 11. 风险

| 风险 | 对策 |
|---|---|
| 摘要调用破坏缓存 | 复用完整前缀 + 低频触发 |
| token 估算偏差 | 用 llm_usage 校准 |
| 记忆噪声 | 只任务类 + top-k |
| 压缩切断 tool 对 | 选择时跳过 tool 对 |
| 模型窗口不同 | per-model 配置 |
| 旧 summary 不兼容 | 双读兼容 |

---

## 12. 建议先做

```text
M0 token_meter（只观测）
M1 tool_pruner（立刻减少上下文）
M2 compact 重写（核心）
```

M0/M1 不改行为，风险最低；M2 完成后 30 轮压测，再开 runtime context。
