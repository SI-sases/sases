# SASES 自愈评估指标

## 背景
自愈能力不能靠感觉判断，必须有量化指标。

## 四个核心指标

### 指标 1：首次成功率
定义：任务在 1 轮内完成的比例
计算：first_try_success / total_tasks
目标：> 80%

### 指标 2：重拆后成功率
定义：重拆 1 次内完成的比例
计算：retry_success / retried_tasks
目标：> 90%

### 指标 3：同类错误重现率
定义：同一错误签名在 7 天内再次出现的比例
计算：error_recurrence / total_errors
目标：< 20%

### 指标 4：记忆命中率
定义：失败记忆被检索并注入到 prompt 的比例
计算：memory_hits / memory_retrievals
目标：> 50%

## 实现方案
swarm_reviews 表加字段：
- is_first_try_success INTEGER
- is_retry_success INTEGER
- error_signature TEXT

统计脚本：scripts/self_healing_report.py
输出：docs/self_healing/YYYYMMDD.md

## 当前基线（待填）
- 首次成功率：约 30%
- 重拆后成功率：约 70%
- 同类错误重现率：约 100%
- 记忆命中率：约 5%

## 改进路径
1. file_patch API 重构 → 消除参数混淆
2. precheck 硬拦截 → 消除侥幸通过
3. agent_behavior 表 → 跨任务学习
4. 行为记忆注入 → 主动防御
