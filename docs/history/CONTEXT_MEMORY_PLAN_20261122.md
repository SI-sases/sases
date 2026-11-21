# SASES 上下文 / 压缩 / 记忆 / 项目库 评估（对齐 DSH）

## 一、结论

需要重构，优先级：

```text
1. 压缩（token 驱动，替换按条数驱动）
2. 运行时上下文注入（统一入口，尾部注入）
3. 工具结果裁剪（pruner）
4. 记忆库 / 项目库（可选 provider）
5. 文档收敛
```

不建议直接照搬 DSH 的“记忆库”——DSH 没有独立记忆包；它靠 **skills + 项目文件 + session log**。  
SASES 的向量记忆/项目库可以保留，但应降级为 **按需检索的上下文 provider**，不要每轮硬塞。

---

## 二、DSH 的做法（已核对安装包）

| 能力 | DSH 实现 |
|---|---|
| 上下文组装 | `dsh-system-prompt`：有序 sections + runtime context，只在必要时刷新 |
| 压缩 | `dsh-compaction-basic`：token 压力触发，摘要替换最老的一段，保留近期原文 |
| 工具裁剪 | `dsh-compaction-tool-result-pruner`：>8192 字符裁成 head 4096 + tail 1024，无模型调用 |
| Token 计量 | `dsh-token-meter`：重放 session log，确定性估算，无模型调用 |
| 会话 | append-only log + projection cache（只加速 UI，不参与模型请求） |
| 记忆 | 没有独立“记忆库”包；靠 skills / 项目指令 / 会话历史 |
| 摘要请求 | 复用 system + tools + 历史前缀，只在尾部加“请总结”，提高缓存命中 |

关键点：

1. 压缩是 **token 压力驱动**，不是“40 条就压”。
2. 先裁工具结果，可能就不需要摘要。
3. 摘要调用本身就是同一前缀的尾部请求。
4. 记忆不是核心上下文，而是按需上下文。
5. 旧历史被摘要替换后，不再进请求。

---

## 三、SASES 现状

| 模块 | 现状 | 问题 |
|---|---|---|
| `agent_compact.py` | 40 条 / 保留 20 条 | 按条数，不按 token |
| `unified_context.maybe_compact` | 另一套压缩 | 与 agent_compact 重复 |
| `unified_context` | 历史 + 摘要 + 记忆 | 新 loop 不走它 |
| `context_service` | 旧 prompt 拼装 | 新 loop 不走它 |
| `memory_service` | 向量记忆 | 新 loop 不调用 |
| `project_service` | 项目库检索 | 新 loop 不调用 |
| 工具结果 | `_spill_large` >20k 落 artifact | 20k 仍太大，没有 8k pruner |
| token 计量 | 粗略字符估算 | 没有 DSH 式 meter |
| 压缩摘要前缀 | 只带 BASE | 没复用完整对话前缀 |

### 最大的问题

**新 agent_loop 只用了 `agent_messages` + `BASE_SYSTEM`，把 SASES 的记忆/项目库/上下文服务全绕过了。**

所以现在有两个世界：

```text
旧路径：memory + project + unified_context + plan_task
新路径：agent_messages + BASE + tools
```

---

## 四、建议的重构

### M1：压缩统一（P0）

1. 只保留一个压缩实现：`agent_compact.py`
2. 触发改为 token 压力：
   - 估算 prompt tokens
   - 超过窗口 80% 触发
   - 保留最近 16%
3. 摘要请求复用：
   - system + tools + 历史原文
   - 只在尾部追加“请总结”
4. `agent_summary` 作为替换事件，不再作为“额外一条 user 消息”拼在前面
5. 删除/停用 `unified_context.maybe_compact`

验收：

- 30 轮会话不爆上下文
- 压缩后缓存命中不明显下降
- 摘要 token < 被替换历史 token 的 30%

### M2：上下文 provider（P0）

新增 `agent_context.py`：

```python
def build_tail_context(user_id, conversation_id, goal):
    # 只返回“本轮真正需要”的动态信息
    return {
        "task_state": ...,
        "memory_hits": ...,
        "project_chunks": ...,
    }
```

注入方式：

```text
system BASE
history...
user 本轮输入
user 【运行时上下文】...   ← 只放这里
```

规则：

- 记忆 top-k ≤3
- 项目 chunk top-k ≤3，每个 ≤600 字
- 任务状态只在变化时注入
- 没有命中就不注入，不占 token

验收：

- 普通聊天不注入记忆
- 任务类才检索项目库
- 上下文尾部不超过 1500 tokens

### M3：工具结果 pruner（P0）

在 agent_loop 里，工具结果超过 8k 字符时：

```text
head 4096 + "\n...[middle pruned]...\n" + tail 1024
```

完整结果仍落 `run_artifacts` / `run_trace`。

验收：

- 大 grep/read 不再把上下文撑爆
- 模型仍能看到开头和结尾

### M4：记忆 / 项目库（P1）

保留，但降级：

- 写入：任务结束后写 `task_result` / `failure_pattern`
- 读取：仅任务类 + 有明确 query
- 去重：hash + 相似度
- 过期：低价值记忆 TTL
- 项目库：静态文档进 `SASES.md` / skill；动态片段才检索

不建议：

- 每轮 recall
- 把 memory 拼进 system
- 把整份项目文档塞进 prompt

### M5：文档收敛（P1）

- 旧文档移到 `docs/history/`
- 只保留：
  - `SASES.md`（项目约束）
  - `docs/STATUS_AND_PLAN_20261122.md`（当前状态）
  - `docs/ARCHITECTURE.md`（更新后）
- 不再让模型读旧版总结；旧文档只作人类考古

---

## 五、旧文档还有没有必要读？

**没有必要作为执行依据。**

原因：

- 多份总结互相覆盖，含已废弃的 `#4:`、旧执行器、旧群服务
- 部分文档有编码损坏
- 新版执行链已经不同

建议：

1. 旧总结全部归档到 `docs/history/`
2. 新建一份“当前事实”文档，只写：
   - 当前入口
   - 当前表
   - 当前约定
3. 模型只读 `SASES.md` + 当前状态文档

---

## 六、总结 / 压缩对 token 的作用

### 有效的部分

- `agent_messages` 压缩后，loader 只取 summary + 近期，旧消息不再进请求
- 摘要本身只保留文本，不保留 tool_calls
- 工具大输出落 artifact，只回指针

### 没做好的部分

- 按条数触发，可能压得太晚或太早
- 摘要请求没有复用完整前缀，摘要调用本身较贵
- 20k 工具结果仍然太大
- 旧 `unified_context` 与新 `agent_compact` 重复，可能重复压缩

### DSH 的节省来自

1. 先裁工具结果（0 模型调用）
2. 压力到了才摘要（1 次调用）
3. 摘要请求复用 warm prefix
4. 摘要替换旧历史，旧历史不再发送
5. projection cache 只省 UI，不省模型 token

---

## 七、需要你确认

1. 记忆库/项目库是否保留为“按需 provider”？
2. 是否允许把旧文档整体归档，只留新状态文档？
3. 压缩阈值用 80% / 保留 16% 是否接受？
4. 工具结果 8k 裁剪是否接受（完整结果仍在 artifact）？

---

## 八、建议顺序

```text
M1 压缩统一       2–3 天
M2 上下文 provider 2 天
M3 工具 pruner     1 天
M4 记忆/项目库     3–5 天
M5 文档收敛        0.5 天
```
