# SASES 未执行内容 · 详细执行方案

> 基线：本地 `27ff9d5`，schema v10；Node-A/B 代码 `6b5f37e75`（docs 未同步）。
> 原则：先一致性验证，再架构收尾，最后质量/可选能力。

---

## 一、当前已完成（不再重复）

- P0/P1/P2 可靠性、安全、审批、检查点、脱敏
- agent_loop / agent_messages / token 压缩 / 工具裁剪
- A2A 统一执行、拒绝/超时回执、脱敏
- 群 @ 接 loop、群 ask、群结果回传
- 审批暂停自动续跑
- ask_user v1/v2
- FTS 记忆/项目检索
- M4 写入 + 低价值过滤 + 180 天清理
- 文档归档 + API/DATABASE 重生成
- 30 轮 96.96%；长任务中途压缩 13,280→260

---

## 二、未执行清单

| ID | 项 | 优先级 | 状态 |
|---|---|---|---|
| R1 | FTS 表启动时确保存在 | P0 | ⬜ |
| R2 | 群/A2A 长任务组合验证 | P0 | ⬜ |
| R3 | 审批路由端到端验证 | P0 | ⬜ |
| R4 | 真实 131k 窗口长任务 | P0 | ⬜ |
| R5 | 旧 executor 退役 | P1 | ⬜ |
| R6 | strict 审核调用裁剪 | P1 | ⬜ |
| R7 | 群蜂群模式/配额策略 | P1 | ⬜ |
| R8 | 群/A2A 流式输出 | P2 | ⬜ |
| R9 | M3/M4 真实任务观察 | P2 | ⬜ |
| R10 | 失败任务写 failure_pattern | P2 | ⬜ |
| R11 | 清理备份目录/脚本 | P2 | ⬜ |
| R12 | 文档同步服务器 | P3 | ⬜ |
| R13 | MCP/PTC/子代理/智维 | P4 | 冻结 |

---

## 三、P0：一致性与验证（1–2 天）

### R1 FTS 表启动确保

问题：

- `memory_fts` / `project_fts` 目前首次检索才创建
- 新节点启动后表可能不存在

方案：

1. `fts_service.ensure()` 暴露幂等初始化
2. `bootstrap.create_app()` 在 `init_db()` 后调用
3. 失败只告警，不阻塞启动

验收：

```text
启动后 sqlite_master 存在 memory_fts/project_fts
空库也能创建
```

### R2 群/A2A 长任务组合

用例：

1. 群 `@调度 执行：读取 data/_longtask_01..10.txt 并汇总`
2. A2A 确认同样任务
3. 观察：
   - 中途压缩
   - 群消息回传 / 好友回传
   - M4 记忆写入
   - 脱敏

验收：

```text
任务完成
summary 1 条
群/好友收到最终结果
memory/notes 各 1 条
```

### R3 审批路由 E2E

当前只测了 `decide + resume_after_approval` 直接调用，未测 HTTP 路由。

方案：

1. 临时把 `SASES_REQUIRE_APPROVAL=1`
2. 发起写文件任务
3. 等 `awaiting_approval`
4. 调 `POST /supervisor/runs/{id}/approve`
5. 验证自动续跑、文件写入、run completed

验收：

```text
approve 后无需重发
pending tool 被真实结果替换
```

### R4 真实 131k 窗口长任务

方案：

- 50 个 5000 行文件，或 20 个 50k 字符文档
- 默认窗口 131072
- 目标：触发一次自动压缩
- 记录：
  - 压缩前后 tokens
  - 压缩次数
  - 任务是否完成
  - 缓存命中

验收：

```text
至少一次 token 压缩
任务完成
无 400/422
```

---

## 四、P1：执行架构收尾（3–5 天）

### R5 旧 executor 退役

现状：

- `agent_loop` 是默认
- `send.py` strict 失败仍可能回退 `swarm_service.plan_task`
- `executor_service` 仍保留旧任务入口

方案：

1. 统计 `plan_task` 调用：`send.py` fallback、`commander`、旧任务表
2. 新增 `SASES_LEGACY_EXEC` 默认 0
3. loop 失败时返回错误，不再自动回退旧四角色
4. 观察 1 周后删除：
   - `swarm_service.plan_task` 路由
   - `executor_service` 旧任务入口
5. 保留：
   - run_journal
   - trace
   - 审批/检查点

验收：

- 10 个任务（读/写/改/失败）
- 审批/回滚
- 定时/A2A
- 无旧路径日志

风险：

- loop 某些任务不如四角色 → 先加 `SASES_LEGACY_EXEC=1` 回退一周

### R6 strict 审核调用裁剪

问题：

- `agent_loop` 严格审核使用完整 `messages`
- 大工具结果时审核请求可能超限
- 未走 tool_pruner

方案：

```python
review_messages = tool_pruner.prune_messages(messages)
```

并限制审核输入：

- 只保留最近 20 条
- tool 结果 8k 裁剪
- 审核输出 500 tokens

验收：

- 大文件写任务审核不超限
- 审核仍返回 PASS/问题

### R7 群蜂群模式/配额策略

现状：

- `@agent` 默认 chat
- `执行：` strict
- 未真正读取 `group_mode=swarm`
- 配额 `check_quota` 已有，但策略不完整

方案：

1. `group_agent_service.reply` 读取：
   - `groups.mode`
   - `is_swarm_enabled`
   - `group_resource_pool.daily_limit`
2. 规则：

| 条件 | 模式 |
|---|---|
| `@agent` 普通 | chat |
| `执行：` | strict + tools |
| swarm + `执行：` | strict + tools，受配额 |
| 配额耗尽 | 拒绝并提示 |

3. 记录 `group_resource_usage`

验收：

- 普通群 chat 不烧工具配额
- swarm 执行受 daily_limit
- 配额耗尽返回明确提示

---

## 五、P2：质量与运维（2–3 天）

### R8 群/A2A 流式输出

现状：

- 聊天有 SSE 流式
- 群/A2A 只有最终结果 + 思考中

方案（可选）：

1. `agent_loop` 增加 `on_token` 回调
2. 群 WS 推送 `group_agent_token`
3. A2A 推送 `a2a_progress` 带增量
4. 前端追加

验收：

- 群智能体回答逐字出现
- 失败可回退最终消息

### R9 M3/M4 真实任务观察

指标：

- 20 个真实任务后：
  - `safety_memory` 新增数
  - `execution_notes` 新增数
  - FTS 命中率
  - 开启/关闭 M3 的 token 差
  - 回答正确率

验收：

- 记忆增长 < 20 条
- 重复 < 10%
- 正确率不下降

### R10 失败任务写 failure_pattern

现状：

- M4 只写 completed
- 失败任务没有记忆

方案：

- `_finish` status failed 时写 `failure_pattern`
- 内容：goal + 失败原因 + 已试方案
- importance 0.5
- 180 天清理

验收：

- 失败任务后续能被 M3 检索到
- 不污染成功记忆

### R11 清理备份目录/脚本

待清理：

```text
_ctx_bak_*
_ctx_v3_bak_*
_exec_v2_bak_*
_menu_v2_bak_*
_run_id_bak_*
_tmp_db_*.py
rollback_*.py
diag_*.py
diag_report.txt
```

步骤：

1. `git archive` 到 `backup/` 或打 tag
2. 删除未引用文件
3. 保留 `scripts/` 正式脚本

验收：

- 根目录无临时脚本
- git status 干净

### R12 文档同步服务器

- 目前服务器代码 `6b5f37e75`，本地 docs `27ff9d5`
- docs 不影响运行，可下次一起同步
- 或单独 bundle 同步

---

## 六、P3/P4：可选与冻结

### 可选

- 记忆/Tool 使用仪表盘
- MCP 管理器
- 群文件/排行榜验收补全

### 冻结（明确不做）

- PTC 运行时
- 多线程/子代理
- 工具生态自动发布
- models/agents 拆表
- 智维空间前端

触发条件：

- 只有出现明确业务需求才解冻

---

## 七、排期

| 周 | 内容 |
|---|---|
| W1 | R1–R4（一致性/长任务/审批） |
| W2 | R5–R7（旧执行器/审核/群策略） |
| W3 | R8–R11（流式/观察/失败记忆/清理） |
| W4 | R12 + 文档/回归 |

---

## 八、总验收

| 项 | 目标 |
|---|---|
| 三端版本 | 同一 commit / schema |
| 长任务 | 131k 窗口可压缩完成 |
| 审批 | 路由级自动续跑 |
| 旧 executor | 不再默认回退 |
| 群执行 | 陪聊/执行/配额明确 |
| 记忆 | 增长可控、可清理 |
| 文档 | API/DATABASE 与代码一致 |
| 回归 | 10/10 保持 |
