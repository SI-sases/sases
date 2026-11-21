# SASES 已执行 / 未完成梳理（2026-11-22）

## 一、版本与现场

| 项 | 值 |
|---|---|
| 本地 HEAD | `dfd2d27` |
| Node-A | `f2e00e6`（schema v9） |
| Node-B | `f2e00e6`（schema v9） |
| 本地 schema | v9 / tables 95 |
| 服务器 schema | v9 / tables 93 |
| 本地工作区 | 仅 `D docs/hlc_health/20261022.md` |
| P2.8 stash | Node-A/B 各保留一份，未 pop |

本地比服务器多 2 个提交：

- `0838f6e` slim report 历史数据
- `dfd2d27` 群“思考中”

---

## 二、已执行

### 1. 可靠性 / 安全（P0–P2）

| 能力 | 状态 |
|---|---|
| run_steps 步骤日志 | ✅ |
| 租约 / 心跳 / 崩溃恢复 | ✅ recovery facade |
| 工具副作用幂等 `tool_effects` | ✅ |
| 先读后写 `fs_observations` | ✅ |
| 审批 `approvals` | ✅ 可选开关 |
| 文件检查点 / 回滚 | ✅ |
| 提示注入防护 | ✅ `<untrusted_tool_output>` |
| 统一脱敏 | ✅ key / path |
| A2A 投递脱敏 | ✅ |
| A2A 拒绝 / 超时回执 | ✅ |

### 2. 执行架构（A0–A6 / C1–C4）

| 能力 | 状态 |
|---|---|
| `agent_messages` append-only | ✅ |
| 双写 / 回填 | ✅ |
| `agent_loop` 单循环 | ✅ |
| fast 默认 / strict 同 loop | ✅ |
| BASE_SYSTEM 统一前缀 | ✅ |
| prompt 固定顺序 | ✅ |
| `prefix_hash` 统计 | ✅ |
| 10 轮缓存 94–97% | ✅ |
| `agent_messages` 压缩 | ✅ |
| 回退开关 `SASES_AGENT_LOOP=0` | ✅ |

### 3. 后端重构（D）

| 能力 | 状态 |
|---|---|
| `message/router.py` | ✅ |
| `message/reply.py` | ✅ |
| `message/ingest.py` | ✅ |
| `swarm/callbacks.py` | ✅ |
| `swarm/tool_output.py` | ✅ |
| `swarm/recovery.py` | ✅ |
| schema 迁移 v6–v9 | ✅ |
| `/version` 跨平台 | ✅ |

### 4. 统一执行入口

| 入口 | 引擎 |
|---|---|
| 聊天 auto/fast | agent_loop |
| 聊天 strict | agent_loop strict |
| A2A 确认 | execution_gateway → strict loop |
| 定时任务 | execution_gateway → strict loop |
| 群 @聊天 | agent_loop fast（无工具） |
| 群 @执行 | agent_loop strict（有工具） |

### 5. 前端 / 交互

| 能力 | 状态 |
|---|---|
| 单一能力胶囊 + `⋯` | ✅ |
| 上下文 chips | ✅ |
| 进度 / 工具 / 审批 / 错误卡 | ✅ |
| 消息动作 复制/重试/编辑 | ✅ |
| 会话头 meta + 切换智能体 | ✅ |
| Markdown / 字号 | ✅ |
| 模型 CRUD | ✅ |
| 流式默认 + 回退 | ✅ |
| 产物 tab | ✅ |
| 定时任务卡（创建后撤销） | ✅ |
| A2A 黄卡状态 / 心跳 | ✅ |
| 群 @ 陪聊/执行提示 | ✅ |
| 群“思考中” | ✅ |
| ask_user 卡片 | ✅ v1/v2 |
| 启动器轨迹 / JSONL / 复制诊断 | ✅ |

### 6. 群聊 / 好友

| 能力 | 状态 |
|---|---|
| A2A 双方自由 + 黄卡 | ✅ |
| A2A 结果回传 | ✅ |
| 群 @ 接 loop | ✅ |
| 群任务 / 红包 / 知识库 | ✅ 基线验证 |
| 群积分读取 | ✅ 修复 |
| 群红包 `packet_type` | ✅ migration v6 |
| 群会话 `-group_id` | ✅ |
| 群“思考中” | ✅ |

### 7. 测试 / 部署

| 项 | 结果 |
|---|---|
| 本地 10 项回归 | ✅ 10/10 |
| A2A 确认 / 拒绝 / 超时 | ✅ |
| 定时任务到点 | ✅ |
| 群聊天 / 执行 / 红包 / 任务 | ✅ |
| Node-A/B 同步 | ✅ v9 |
| 云端功能测试 | 按用户要求未做 |

---

## 三、未完成 / 已知缺口

### P0：版本收尾

1. 本地 `0838f6e`、`dfd2d27` 未同步到 Node-A/B
2. Node-A/B 无 `tool_usage` / `agent_questions` 新表（本地 tables 95 vs 93）
3. P2.8 stash 未处理：本地已更新，stash 属旧版本，建议归档不恢复

### P1：执行闭环

4. **审批暂停不自动续跑**
   - loop 返回 `awaiting_approval`
   - 审批后需要用户重发
5. **聊天 ask_user 无 run_id**
   - v2 只能对 A2A/定时 resume
   - 聊天仍走“回答=新消息”
6. **群 ask_user 未接**
   - 群会话是 `-group_id`，没有对应 run
7. **群 @ 蜂群模式未细分**
   - 当前只看 `执行：`
   - 未读 `group_mode=swarm` / 资源池配额上限

### P2：质量 / 成本

8. **旧 executor 未退役**
   - `executor_service` / `swarm_service.plan_task` 仍保留
   - strict 失败会回退旧路径
9. **工具瘦身未执行**
   - 已出报告：9 个零使用
   - 决定暂不隐藏（extension 本来不进主提示词）
10. **长会话缓存未压测**
    - 目前 10 轮 94–97%
    - 未测 30–50 轮 + 压缩后的缓存
11. **群跨实例 502**
    - 已知遗留，未处理
12. **群智能体无流式**
    - 思考中提示有，逐字输出没有

### P3：冻结 / 可选

13. MCP 管理器
14. PTC 运行时
15. 多线程 / 子代理
16. 工具生态自动发布
17. models / agents 拆表
18. 智维空间前端（仅后端 route + 表）

---

## 四、未完成部分执行方案

### 阶段 1：版本收尾（0.5 天）

1. 本地 bundle 同步到 Node-A/B
2. 重启，确认 `/version` = `dfd2d27`
3. 确认新表 `tool_usage_daily`、`agent_questions` 存在
4. P2.8 stash 归档：
   - `git stash show -p > /root/p28_archive.patch`
   - 保留，不 pop
5. 验收：三端 commit/schema 一致，服务 active

### 阶段 2：审批暂停自动续跑（1–2 天）

1. 新增 `pending_actions` 或复用 `approvals`
2. loop 捕获 `ApprovalRequired` 时保存：
   - run_id / conversation / step / tool / args
3. `POST /supervisor/runs/{id}/approve` 后：
   - 写 tool 结果“已批准”
   - `asyncio.create_task(agent_loop.run(..., resume=True))`
4. loop 支持 `resume=True`：不重复追加用户消息
5. 验收：审批后原 run 自动继续，不要求重发

### 阶段 3：聊天 ask_user 同 run（1 天）

1. chat 首次 ask 时创建 supervisor run（或轻量 `agent_runs`）
2. 问题表写 run_id
3. answer API 走 `resume_run`
4. 验收：聊天提问 → 回答 → 同一 run 继续

### 阶段 4：群执行策略（1–2 天）

1. `group_agent_service` 读取：
   - `group_mode=swarm`
   - 资源池 `daily_limit`
2. 规则：
   - `@agent` 默认 chat
   - `执行：` strict + tools
   - swarm + `执行：` 允许工具，但受配额
3. 群 ask_user：回答走群消息，不 resume run
4. 验收：群聊天不烧配额；群执行受配额

### 阶段 5：旧执行器退役（3–5 天）

1. 统计旧路径调用：`swarm_service.plan_task`
2. 把 strict 回退改为“loop + 提示失败”，不再回退四角色
3. 移除 `executor_service` 的旧任务入口
4. 保留 `run_journal`/trace/审批
5. 验收：10 任务 + 审批 + 回滚全部通过

### 阶段 6：长会话与工具（观察）

1. 30 轮会话压测：
   - 缓存率
   - 压缩前后
   - 首字延迟
2. 30 天后看 `tool_usage_daily`：
   - 再决定隐藏/归档
3. 群跨实例 502：单独排期

### 阶段 7：可选（P3）

- MCP 管理器：后端 client + 启动器右侧 UI
- PTC：按需
- 智维空间：先冻结

---

## 五、建议顺序

```text
1. 版本收尾（本地 → Node-A/B）       0.5 天
2. 审批自动续跑                      1–2 天
3. 聊天 ask_user 同 run              1 天
4. 群执行策略                        1–2 天
5. 旧执行器退役                      3–5 天
6. 长会话压测 / 工具观察             持续
7. MCP / PTC / 智维空间              可选
```

## 六、验收总表

| 项 | 目标 |
|---|---|
| 三端版本 | 同一 commit / schema |
| 审批 | 批准后自动续跑 |
| ask_user | A2A/定时/聊天都可续跑 |
| 群执行 | 默认陪聊，执行受配额 |
| 旧执行器 | 不再作为默认回退 |
| 缓存 | 30 轮 ≥90% |
| 回归 | 10/10 保持 |
