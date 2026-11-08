import sqlite3
import datetime

print("开始为 P2 建表...")

conn = sqlite3.connect('users.db')
cur = conn.cursor()

# 1. nodes 表
cur.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        node_name TEXT,
        role_type TEXT DEFAULT 'app_node',
        public_key TEXT,
        capabilities TEXT,
        status TEXT DEFAULT 'offline',
        last_heartbeat TEXT,
        created_at TEXT NOT NULL
    )
""")

# 2. cognitive_rules 表
cur.execute("""
    CREATE TABLE IF NOT EXISTS cognitive_rules (
        rule_id TEXT PRIMARY KEY,
        domain_main TEXT NOT NULL,
        domain_sub TEXT,
        rule_content TEXT NOT NULL,
        trigger_context TEXT,
        confidence REAL DEFAULT 0.5,
        applied_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        source_pattern_ids TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )
""")

# 3. rule_tool_bindings 表
cur.execute("""
    CREATE TABLE IF NOT EXISTS rule_tool_bindings (
        binding_id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT NOT NULL,
        tool_id TEXT NOT NULL,
        usage_context TEXT,
        priority INTEGER DEFAULT 0,
        FOREIGN KEY(rule_id) REFERENCES cognitive_rules(rule_id)
    )
""")

print("✅ 3 张 P2 核心表建表完成！")

# 4. 灌入常识种子数据
now = datetime.datetime.now().isoformat()
seeds = [
    ("rule_seed_001", "dev", "code_edit", "修改代码前必须先 file_read 确认原文，不要凭记忆构造锚点。", '{"tools_involved": ["file_patch"]}', 1.0),
    ("rule_seed_002", "dev", "code_edit", "file_patch 后必须 verify_syntax。", '{"tools_involved": ["file_patch"]}', 1.0),
    ("rule_seed_003", "dev", "search", "全盘扫描时，禁止使用 dir /s /b，必须先限定目录。", '{"tools_involved": ["dir_tree"]}', 0.9)
]

for s in seeds:
    cur.execute("INSERT OR REPLACE INTO cognitive_rules (rule_id, domain_main, domain_sub, rule_content, trigger_context, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (s[0], s[1], s[2], s[3], s[4], s[5], now))

conn.commit()
print("✅ 常识库种子数据已写入！")

# 5. 验证
cur.execute("SELECT rule_id, rule_content FROM cognitive_rules")
print("\n当前常识库内容：")
for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]}")

conn.close()
print("\n全部完成！")