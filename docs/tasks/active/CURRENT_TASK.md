当前任务：P2 建表。
目标：建 nodes/api_registry/cognitive_rules 等表，不破坏现有功能。
目标：建 nodes/api_registry/cognitive_rules 等表，不破坏现有功能。
验收：PRAGMA table_info(nodes) 有字段；现有功能跑通。
坑点：file_patch 前必 file_read；大段替换固化成 scripts/xxx.py；改 core/ 必须重启；不动 users.db 结构外的东西。
回滚：git checkout <pre-p2>。

## 归档纪律

- 任务结束时只输出 [SUMMARY]，禁止自动归档
- 用户明确说"执行归档"时，才调：python scripts/archive_task.py --task p2-build
- 归档前必须先跑 --dry-run
- 归档后 task_context 残留和 task__ 分片残留必须都为 0
