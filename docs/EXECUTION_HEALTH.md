# SASES 执行质量诊断

生成时间：2026-10-03 10:34

> 本文档由 `scripts/gen_health_doc.py` 自动生成
> 运行命令：`python scripts/gen_health_doc.py`
> 建议频率：每周一次，或每次功能上线后

## 诊断输出

```
============================================================
SASES 知识库数据体检
============================================================

【1】swarm_reviews（每步审核日志）
  总记录数: 4122
    success: 3465
    failed: 520
    blocked: 71
    error: 60
    timeout: 3
    skipped: 3
  审核结果分布:
    pass: 3559
    retry: 563

【2】失败命令重复率（核心指标）
  失败最多的命令 TOP 10:
    [189次] file_patch
    [72次] run_python
    [19次] file_read
    [18次] verify_syntax
    [11次] ...
    [6次] findstr /n /c:"MODEL_NAME" core/config.py
    [5次] grep_code
    [5次] findstr /n /c:"_is_external_safe" harness_modules/verify_syn
    [4次] verify_patch
    [4次] restart_pending
  失败命令去重比: 232/591 = 0.39
  → 比值越低，重复失败越多，预测越有意义

【3】失败原因类型分布
    [99次] 查询无结果（正常）
    [71次] 命令被安全策略拒绝
    [59次] 目标文件不存在，路径可能有误
    [37次] 命令状态: failed | Harness 失败:
    [8次] 命令状态: failed | 文件名、目录名或卷标语法不正确。
    [8次] 命令状态: failed | Harness 失败: 缺少 file_path 参数
    [6次] 命令状态: failed | Harness 失败: 禁止修改受保护文件: core/services/executor_service.p
    [6次] 命令状态: failed | Harness 失败: position 必须是 before/after/replace_line，收到: 
    [5次] 命令状态: failed | Harness 失败: missing file_path
    [5次] 命令状态: failed
    [4次] 命令状态: failed | Harness 失败: 缺少 pattern
    [4次] 命令状态: failed | Harness 失败: 模块 '文件复制' 需要危险权限 'file_write'，但当前未被授权，已阻止执行
    [4次] 命令状态: failed | Harness 失败: 文件非空时必须提供：
  - anchor_pattern（锚点模式，推荐）
  - 
    [4次] 命令状态: failed | Harness 失败: 原片段在 core/services/swarm_service.py 中出现 2 次
    [4次] 命令状态: failed | Harness 失败: name 'r' is not defined

【4】swarm_pending_tasks（任务级）
  总任务数: 21
    cancelled: 8
    completed: 12
    interrupted: 1

【5】supervisor_runs（自主运行）
  总运行数: 310
    cancelled: 9
    completed: 222
    error: 10
    interrupted: 59
    rejected: 6
    timeout: 4

【6】safety_memory（记忆库）
  总记忆数: 1785
    task_result: 1536
    failure_pattern: 222
    task_state: 27

【7】execution_notes（执行笔记）
  总数: 1195
    partial: 115
    success: 1080

【8】interaction_patterns（经验库）
  总数: 103
    blocked: 3
    failure: 26
    sequence: 35
    success: 24
    syntax: 15
  按领域分布:
    dev: 103
  高置信高命中的 pattern: 2

【9】failed_cases（失败案例）
  总数: 0

【10】candidate_rules（候选规则）
  表不存在（正常，尚未建）

============================================================
综合判断
============================================================

执行层: 成功 3465 / 失败 591
TOP 10 命令覆盖失败数: 333 / 591 = 56.3%

【结论】TOP 10 覆盖率高，失败高度集中，预测价值高

```

## 如何解读

| 指标 | 含义 | 优化方向 |
|------|------|---------|
| 失败去重比 | 失败命令种类 / 失败总数 | 比值越低，重复失败越多，越值得优化 |
| TOP 10 覆盖率 | TOP 10 失败命令占全部失败的比例 | > 50%，说明失败高度集中 |
| 安全拒绝次数 | blocked 状态的次数 | 过高说明策略太严 |
| 文件不存在 | 查询类失败的常见原因 | 三者应先 dir_tree 确认 |

## 后续动作

- 若 file_patch 失败率高 → 工具手册补充"锚点技巧"
- 若安全拒绝多 → 检查权限设计
- 若某类失败突然增多 → 检查近期代码改动
