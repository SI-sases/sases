# DSH 上下文能力落地记录（M0–M4）

## 已完成

### M0 token meter

- `core/services/token_meter.py`
- 确定性估算：ASCII `len/4`，CJK `count/1.5`，消息/工具开销
- `pressure_budget()`：
  ```text
  threshold = min(W*0.8, W-O-B)
  retain    = (W-O)*0.16
  ```
- 默认：`W=131072, O=4096, B=32768`

### M1 tool pruner

- `core/services/tool_pruner.py`
- 只裁 `tool` 消息：
  ```text
  >8192 字符 → head 4096 + ...[middle pruned]... + tail 1024
  ```
- 只影响本轮请求，`agent_messages` 保留完整原文
- 开关：`SASES_TOOL_PRUNER=0` 关闭，默认开

### M2 token 压缩

- `agent_compact.py`
- 开关：`SASES_TOKEN_COMPACT=0` 回退旧条数压缩，默认开
- 触发：token 压力 > threshold
- 保留最近 `retain_tokens`
- 摘要请求复用 `system + tools + 旧历史` 前缀，`tool_choice="none"`
- 写回：
  - 旧消息 `compacted=1`
  - 新增一条 assistant `【历史摘要】...`
  - `agent_summary` 记录 `summary_message_id / tokens_before / tokens_after / reason`
- loader：
  ```text
  [system] + [summary assistant] + compacted=0 的消息
  ```

### M3 runtime context

- `agent_context.py`
- 默认只注入“当前任务状态”
- 记忆/项目检索需 `SASES_RUNTIME_RECALL=1`
- 关键词兜底：`keyword_search.py`（中文 bigram + 英文词）
- 只拼在请求尾部，不写 `agent_messages`
- 开关：`SASES_RUNTIME_CONTEXT=1`，默认开
- 记忆/项目：`SASES_RUNTIME_RECALL=1`，默认开

A/B（10 个问题）：

| 项 | 关闭 | 开启 |
|---|---|---|
| 成功 | 8/10 | 8/10 |
| prompt tokens | 9,017 | 9,402 |
| cached | 6,912 | 7,424 |

开启 +4.3% tokens，质量无量化提升；本地缺 `bge-small-zh-onnx`，语义记忆不可用，关键词记忆噪声大。  
结论：默认关闭；需要时只开任务状态，记忆/项目再单独开 `SASES_RUNTIME_RECALL=1`。

### M4 memory/project 写回

- `execution_gateway._finish`
- run 完成后写：
  - `memory_service.remember(task_result)`
  - `project_service.import_execution_note`
- 开关：`SASES_MEMORY_WRITE=1`，默认关

## 实测

### 30 轮（窗口 8000，未到压力）

```text
30/30 成功
60 次 LLM 调用
prompt 395,502
cached 383,488
命中 96.96%
messages 120，compacted 0
```

说明：30 轮短会话没有到 60k 默认阈值，不压缩是正确的。

### 强制 token 压缩（窗口 1500）

```text
60 条历史 / 1440 tokens
→ covered 48 条
→ history 13 条（摘要 + 近期）
→ tokens_before=1440, tokens_after=185
```

### 工具对边界

```text
15 组 assistant tool_calls + tool result
4619 tokens → covered 47 条
history 14 条，摘要 + 近期
无 tool_call_id 400/422
```

### 工具裁剪

```text
12000 字符 → 5143 字符
head 4096 + marker + tail 1024
```

## 当前开关

| 开关 | 默认 | 说明 |
|---|---|---|
| `SASES_TOOL_PRUNER` | 1 | 工具裁剪 |
| `SASES_TOKEN_COMPACT` | 1 | token 压缩 |
| `SASES_RUNTIME_CONTEXT` | 1 | 任务状态注入 |
| `SASES_RUNTIME_RECALL` | 1 | 记忆/项目注入 |
| `SASES_MEMORY_WRITE` | 0 | 结果写回记忆 |
| `SASES_CTX_WINDOW` | 131072 | 窗口 |
| `SASES_CTX_OUTPUT` | 4096 | 输出预留 |
| `SASES_CTX_HEADROOM` | 32768 | 压力余量 |

## 未完成

1. M5：旧文档归档、30 轮压测
2. M3/M4 默认开启前的 A/B
3. 压缩摘要质量评估
4. 旧 `unified_context.maybe_compact` 停用/删除
5. 工具裁剪后的大结果可观测性（trace 标记）

## 验收

| 项 | 状态 |
|---|---|
| 30 轮不爆 | 待压测 |
| 缓存 ≥90% | 待压测 |
| 摘要 ≤30% | 待压测 |
| 普通聊天不注入记忆 | 默认关，符合 |
| 工具 ≤8k | 已实现 |

## 提交

- `a5cc097` M0
- `1657c24` M1
- `77f7878` M2
- `ee5c6c8` M3
- `1821ca1` M4
- `7ee2bde` M2 默认开启

## 部署

Node-A / Node-B：`7ee2bdef`，schema v10。
