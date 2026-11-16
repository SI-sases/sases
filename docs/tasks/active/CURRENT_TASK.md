当前任务：P2 建表。
目标：建 nodes/api_registry/cognitive_rules 等表，不破坏现有功能。
涉及：core/db.py, core/migrations.py, users.db。
验收：PRAGMA table_info(nodes) 有字段；现有功能跑通。
坑点：file_patch 前必 file_read；大段替换固化成 scripts/xxx.py；改 core/ 必须重启；不动 users.db 结构外的东西。
回滚：git checkout <pre-p2>。