# SASES 计划能力优化方案（参考 DSH）

## 一、结论

SASES 30 步只审计、不产出，不是单纯“任务定义失败”，而是缺少 DSH 的**计划对象**：

```text
DSH: todo_write / plan mode / goal / workflow
SASES: 只有 goal + 原始对话
```

指挥官把 P5 拆成 4 步，是**外部替它做计划**，不是 SASES 自己的能力。

---

## 二、DSH 的对应能力

### 1. todo_write

DSH 的 `dsh-tool-todo` 提供模型可见的 `todo_write`：

```json
{
  "todos": [
    {"content": "审计依赖", "status": "in_progress"},
    {"content": "实现最小原型", "status": "pending"},
    {"content": "验证", "status": "pending"}
  ]
}
```

特点：

- 整表替换，不搞局部更新
- 状态：pending / in_progress / completed
- 存在 session log，刷新/重启/压缩后可恢复
- UI 可见
- 只允许一个 in_progress（或配置并行）
- 每次调用有明确的结构化结果

### 2. plan mode

`dsh-plan-mode`：

- `/plan` 进入探索/设计
- `exit_plan_mode` 提交完整计划
- 用户 Approve / Keep planning

它不限制工具，但把“先计划、后执行”变成可见状态。

### 3. goal / workflow

DSH 的 goal 持久化长期目标，workflow 做多阶段编排。  
SASES 目前只有 `supervisor_runs.goal`，没有计划对象。

---

## 三、SASES 为什么 30 步

当前 `agent_loop`：

```text
system = BASE_SYSTEM
history = 对话
goal = 用户原话
```

没有：

- 计划列表
- 当前步骤
- 完成条件
- 阶段预算
- 阻塞条件

模型只能靠上下文自己“记着”，于是不断审计。

---

## 四、要实现的最小计划能力

### Phase 1：todo_write + 计划门禁

新增一个工具，不新增一堆：

```text
todo_write
  todos: [{content, status}]
```

存储：

```sql
agent_todos(
  id,
  conversation_id,
  run_id,
  items_json,
  updated_at
)
```

规则：

- 整表替换
- 最多 1 个 in_progress
- 每次更新返回计数
- 当前计划注入到下一轮上下文
- 最终回答前如果有 pending/in_progress，禁止结束
- 预算步数用完后返回 failed，并保留计划

### Phase 2：系统提示

`BASE_SYSTEM` 增加：

```text
多步骤任务（>=3 步）必须先 todo_write 列出步骤和验收条件。
每完成一步更新 todo。
发现依赖缺失，立即标记 blocked 并报告，不要继续无关审计。
不要在 todo 有 pending 时宣布完成。
```

### Phase 3：任务预算

`todo_write` 不增加预算字段，预算来自任务参数：

```text
max_steps=8
max_audit_steps=2
```

agent_loop 统计：

```text
审计类工具：file_read/grep/dir_tree
执行类工具：file_write/run_python/verify
```

规则：

```text
连续 3 步只读审计且没有 todo 更新 → 注入“先给计划或 blocked”
```

### Phase 4：计划审批（可选）

不新建 plan 系统，复用：

```text
todo_write 生成计划
ask_user 让用户 Approve / 修改
```

这样只增加一个工具，不增加 plan_mode 全套。

---

## 五、减法原则

### 新增

```text
todo_write 一个入口
```

### 减掉

- P5 关闭：无全量注入，不再开发
- P3/P4 不从零写：只用 MCP / FFmpeg / provider
- 不再给 P3-P5 一个大任务
- 不再用 30 步审计代替 blocked
- 不再由指挥官拆分代替 SASES 计划

### 净效果

```text
工具 +1
无效步骤 -20 以上
```

---

## 六、验收

### 用例 1：三步任务

```text
任务：改 i18n + 验证
要求：Step 1 必须 todo_write
最终：pending=0
步数：<=8
```

### 基准结果（2026-11-22）

```text
10/10 成功
34 步
prompt 101,512
todo 使用 3/10（仅复杂任务）
```

计划门禁后的目标：

```text
通过率 100%
步数 <=35
token <=120k
```

### 用例 2：依赖缺失

```text
任务：做视频剪辑
要求：先 todo_write
发现无 FFmpeg/MCP → blocked
步数：<=5
不允许继续 grep 20 次
```

### 用例 3：完成门禁

```text
todo 还有 pending
模型试图最终回答
→ 注入“还有未完成项”
→ 继续或 failed
```

---

## 七、P3/P4/P5 新任务卡

### P3

```text
预算 5 步
1. todo_write
2. 检查 ffmpeg/MCP
3. 有 → 最小 video_edit manifest
4. 无 → blocked
5. 报告
```

### P4

```text
预算 5 步
1. todo_write
2. 检查 Windows-MCP/CUA provider
3. 有 → 一个 cua 入口设计
4. 无 → blocked
5. 报告
```

### P5

```text
已关闭，无全量注入，0 代码
```

---

## 八、实施顺序

1. 建 `agent_todos` 表 + 迁移
2. 写 `todo_write` 工具
3. `agent_loop` 注入计划 + 最终门禁
4. 系统提示 + 审计步数限制
5. 用三步任务验收
6. 再用 P3/P4 验收 blocked 能力
