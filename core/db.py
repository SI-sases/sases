# core/db.py
import sqlite3
import os
from contextlib import contextmanager

_env_db = os.environ.get("SASES_DB_PATH")
DB_PATH = os.path.abspath(_env_db) if _env_db else os.path.join(os.path.dirname(__file__), '..', 'users.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if os.environ.get("SASES_DISABLE_FK", "false").lower() not in ("1", "true", "yes"):
        conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_db():
    return get_connection()

@contextmanager
def db_cursor(commit=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        conn.close()

def _ensure_column(cur, table: str, column: str, definition: str):
    if "CURRENT_TIMESTAMP" in definition.upper():
        definition = definition.replace("CURRENT_TIMESTAMP", "NULL")
    cur.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cur.fetchall()]
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    with db_cursor(commit=True) as cur:
        # ========== 用户表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                sases_id TEXT,
                credits REAL DEFAULT 0,
                gender TEXT,
                region TEXT,
                signature TEXT,
                onboarding_day INTEGER DEFAULT 1,
                onboarding_completed TEXT DEFAULT '[]',
                onboarding_started_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ensure_column(cur, "users", "email", "TEXT")
        _ensure_column(cur, "users", "sases_id", "TEXT")
        _ensure_column(cur, "users", "credits", "REAL DEFAULT 0")
        _ensure_column(cur, "users", "gender", "TEXT")
        _ensure_column(cur, "users", "region", "TEXT")
        _ensure_column(cur, "users", "signature", "TEXT")
        _ensure_column(cur, "users", "onboarding_day", "INTEGER DEFAULT 1")
        _ensure_column(cur, "users", "onboarding_completed", "TEXT DEFAULT '[]'")
        _ensure_column(cur, "users", "onboarding_started_at", "TEXT")

        # ========== API Key 表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 知识库表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                branch_a TEXT,
                branch_b TEXT,
                solution TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                source_task_id INTEGER,
                contributor_id INTEGER,
                hit_count INTEGER DEFAULT 0,
                quality_score INTEGER DEFAULT 0,
                last_used_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ensure_column(cur, "knowledge_base", "source_task_id", "INTEGER")
        _ensure_column(cur, "knowledge_base", "contributor_id", "INTEGER")
        _ensure_column(cur, "knowledge_base", "hit_count", "INTEGER DEFAULT 0")
        _ensure_column(cur, "knowledge_base", "quality_score", "INTEGER DEFAULT 0")
        _ensure_column(cur, "knowledge_base", "last_used_at", "TEXT")

        # ========== 贡献日志表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contribution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT,
                event_type TEXT DEFAULT 'manual',
                points REAL DEFAULT 0,
                model_source TEXT DEFAULT 'api',
                model_id TEXT,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "contribution_log", "action", "TEXT")
        _ensure_column(cur, "contribution_log", "event_type", "TEXT DEFAULT 'manual'")
        _ensure_column(cur, "contribution_log", "points", "REAL DEFAULT 0")
        _ensure_column(cur, "contribution_log", "model_source", "TEXT DEFAULT 'api'")
        _ensure_column(cur, "contribution_log", "model_id", "TEXT")
        _ensure_column(cur, "contribution_log", "detail", "TEXT")
        _ensure_column(cur, "contribution_log", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

        _ensure_column(cur, "contribution_log", "origin_node", "TEXT DEFAULT 'node-A'")

        _ensure_column(cur, "contribution_log", "logical_clock", "INTEGER DEFAULT 0")

        # ========== 模型配置表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS model_configs (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                model_type TEXT NOT NULL,
                name TEXT NOT NULL,
                provider TEXT,
                api_key_encrypted TEXT,
                node_url TEXT,
                model_name TEXT,
                capabilities TEXT,
                is_shared INTEGER DEFAULT 0,
                visibility TEXT DEFAULT 'private',
                price REAL DEFAULT 1.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 会话表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                agent_id TEXT,
                title TEXT DEFAULT '新会话',
                mode TEXT DEFAULT 'normal',
                unread_count INTEGER DEFAULT 0,
                is_pinned INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "conversations", "mode", "TEXT DEFAULT 'normal'")
        _ensure_column(cur, "conversations", "unread_count", "INTEGER DEFAULT 0")
        _ensure_column(cur, "conversations", "is_pinned", "INTEGER DEFAULT 0")

        # ========== 消息表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                sender_agent_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        _ensure_column(cur, "messages", "sender_agent_id", "TEXT")

        # ========== 好友关系表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                friend_agent_id TEXT NOT NULL,
                target_user_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (target_user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "agent_friendships", "target_user_id", "INTEGER")

        # ========== 群组表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                mode TEXT DEFAULT 'normal',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "groups", "global_group_id", "TEXT")
        _ensure_column(cur, "groups", "origin_node", "TEXT")
        _ensure_column(cur, "groups", "mode", "TEXT DEFAULT 'normal'")
        _ensure_column(cur, "groups", "is_pinned", "INTEGER DEFAULT 0")

        # ========== 群成员表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER,
                agent_id TEXT,
                role TEXT DEFAULT 'member',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "group_members", "agent_id", "TEXT")
        _ensure_column(cur, "group_members", "last_read_at", "TEXT")
        _ensure_column(cur, "group_members", "origin_node", "TEXT")
        _ensure_column(cur, "group_members", "user_sases_id", "TEXT")

        _ensure_column(cur, "group_members", "nickname", "TEXT")
        _ensure_column(cur, "group_members", "is_muted", "INTEGER DEFAULT 0")

        # ========== 群消息表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                sender_id INTEGER,
                sender_agent_id TEXT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "group_messages", "sender_agent_id", "TEXT")
        _ensure_column(cur, "group_messages", "global_msg_id", "TEXT")
        _ensure_column(cur, "group_messages", "origin_node", "TEXT")


        # ========== 蜂群模式：群任务表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                global_task_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                task_category TEXT DEFAULT 'text',
                created_by INTEGER NOT NULL,
                reward_credits REAL NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'open',
                selected_submission_id INTEGER,
                judging_deadline TEXT,
                reject_reason TEXT,
                last_repushed_at TEXT,
                repush_count INTEGER DEFAULT 0,
                origin_node TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # ========== 蜂群模式：任务提交表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_task_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                global_submission_id TEXT,
                submitted_by INTEGER NOT NULL,
                agent_id TEXT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                is_disqualified INTEGER DEFAULT 0,
                edited_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES group_tasks(id),
                FOREIGN KEY (submitted_by) REFERENCES users(id)
            )
        """)

        # ========== 蜂群模式：群积分流水 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_credit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER,
                amount REAL NOT NULL,
                tx_type TEXT NOT NULL,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ========== 蜂群模式：成员质押 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_stakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                withdrawn_at TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 蜂群模式：空投日志 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_airdrop_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                airdrop_date TEXT NOT NULL,
                activity_score REAL NOT NULL,
                rank INTEGER,
                amount REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_airdrop_group_date
            ON group_airdrop_log(group_id, airdrop_date)
        """)

        # ========== 蜂群模式：groups 扩展字段 ==========
        _ensure_column(cur, "groups", "credits", "REAL DEFAULT 0")
        _ensure_column(cur, "groups", "staked_credits", "REAL DEFAULT 0")
        _ensure_column(cur, "groups", "features", "TEXT DEFAULT '{}'")
        _ensure_column(cur, "groups", "red_packet_hour", "INTEGER DEFAULT 20")
        _ensure_column(cur, "groups", "red_packet_audience", "TEXT DEFAULT 'all'")
        _ensure_column(cur, "groups", "airdrop_enabled", "INTEGER DEFAULT 1")
        _ensure_column(cur, "groups", "airdrop_paused_until", "TEXT")

        _ensure_column(cur, "groups", "last_red_packet_date", "TEXT")
        _ensure_column(cur, "groups", "pool_packet_amount", "REAL DEFAULT 0")
        _ensure_column(cur, "groups", "pool_packet_count", "INTEGER DEFAULT 5")

        _ensure_column(cur, "groups", "announcement", "TEXT")

        _ensure_column(cur, "groups", "logical_clock", "INTEGER DEFAULT 0")

        # ========== 蜂群模式：group_messages 扩展字段 ==========
        _ensure_column(cur, "group_messages", "message_type", "TEXT DEFAULT 'text'")
        _ensure_column(cur, "group_messages", "related_id", "INTEGER")
        _ensure_column(cur, "group_messages", "extra_data", "TEXT")

        _ensure_column(cur, "group_messages", "logical_clock", "INTEGER DEFAULT 0")


        # ========== 统一知识库文档表（群知识库/工具手册/项目文档） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL DEFAULT 'group',
                group_id INTEGER,
                title TEXT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'doc',
                tags TEXT,
                source_type TEXT DEFAULT 'manual',
                source_id TEXT,
                contributor_id INTEGER,
                hit_count INTEGER DEFAULT 0,
                visibility TEXT DEFAULT 'group',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_kdocs_scope_group ON knowledge_docs(scope, group_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_kdocs_category ON knowledge_docs(category)")

        # ========== 群汇报队列（待补充的知识缺口） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_report_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                asked_by INTEGER,
                anonymous INTEGER DEFAULT 0,
                hit_knowledge_id INTEGER,
                status TEXT DEFAULT 'pending',
                resolved_kb_id INTEGER,
                resolved_by INTEGER,
                resolved_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grq_group_status ON group_report_queue(group_id, status)")


        # ========== 群资源池（蜂群模式：智能体绑定模型） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_resource_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                agent_id TEXT NOT NULL,
                model_id TEXT,
                daily_limit INTEGER DEFAULT 100,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_grp_pool_agent ON group_resource_pool(group_id, agent_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grp_pool_model ON group_resource_pool(model_id)")


        # ========== 待批准邀请 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_invite_pending (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                invitee TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                resolved_by INTEGER
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grp_invite_status ON group_invite_pending(group_id, status)")



        # ========== 群资源使用日志 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_resource_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                agent_id TEXT,
                model_id TEXT,
                tokens_used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grp_usage_date ON group_resource_usage(group_id, user_id, created_at)")






        # ========== 群红包主表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_red_packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                source_type TEXT DEFAULT 'user',
                total_amount REAL NOT NULL,
                total_count INTEGER NOT NULL,
                claimed_count INTEGER DEFAULT 0,
                remaining_amount REAL NOT NULL,
                message TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grp_rp_group ON group_red_packets(group_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_grp_rp_expires ON group_red_packets(status, expires_at)")

        # ========== 群红包领取记录 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_red_packet_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                packet_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                claimed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_grp_rpc_pid_uid ON group_red_packet_claims(packet_id, user_id)")




        # ========== 市场订单表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_type TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'open',
                accepted_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (accepted_by) REFERENCES users(id)
            )
        """)

        # ========== AI 圈帖子表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_circle_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                owner_user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT DEFAULT 'daily',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id)
            )
        """)

        # ========== 交易表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                tx_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                expires_at TEXT,
                claimed_at TEXT,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "transactions", "expires_at", "TEXT")
        _ensure_column(cur, "transactions", "claimed_at", "TEXT")

        _ensure_column(cur, "transactions", "origin_node", "TEXT DEFAULT 'node-A'")

        _ensure_column(cur, "transactions", "logical_clock", "INTEGER DEFAULT 0")

        # ========== 账本版本表（B 阶段预留） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ledger_versions (
                node_id TEXT PRIMARY KEY,
                version INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


# ========== 节点注册表（B 阶段） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS node_registry (
                node_id TEXT PRIMARY KEY,
                public_key TEXT,
                url TEXT,
                role TEXT,
                status TEXT DEFAULT 'active',
                first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


        
        # ========== 空间节点表（SpaceService） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS space_nodes (
                node_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                node_type TEXT DEFAULT 'harness',
                capabilities TEXT,
                endpoint TEXT,
                icon TEXT,
                owner_id TEXT DEFAULT 'system',
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reputation REAL DEFAULT 1.0,
                success_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'unknown'
            )
        """)



        # ========== 积分锚定表（蜂群预留） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_anchors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                anchor_hash TEXT NOT NULL,
                record_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_anchors_node_ts ON credit_anchors(node_id, ts)")

        # ========== 种子任务表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seed_tasks (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                domain TEXT,
                difficulty TEXT DEFAULT 'medium',
                user_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 安全记忆表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS safety_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                full_data TEXT,
                agent_id TEXT,
                user_id INTEGER NOT NULL,
                group_id INTEGER,
                importance REAL DEFAULT 0.5,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)
        _ensure_column(cur, "safety_memory", "memory_type", "TEXT NOT NULL")
        _ensure_column(cur, "safety_memory", "content", "TEXT NOT NULL")
        _ensure_column(cur, "safety_memory", "full_data", "TEXT")
        _ensure_column(cur, "safety_memory", "agent_id", "TEXT")
        _ensure_column(cur, "safety_memory", "user_id", "INTEGER NOT NULL")
        _ensure_column(cur, "safety_memory", "group_id", "INTEGER")
        _ensure_column(cur, "safety_memory", "importance", "REAL DEFAULT 0.5")
        _ensure_column(cur, "safety_memory", "tags", "TEXT")
        _ensure_column(cur, "safety_memory", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
        _ensure_column(cur, "safety_memory", "expires_at", "TEXT")
        _ensure_column(cur, "safety_memory", "task_id", "TEXT")
        _ensure_column(cur, "safety_memory", "embedding", "BLOB")
        _ensure_column(cur, "safety_memory", "content_hash", "TEXT")

        # ========== 工作日志表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS work_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                agent_id TEXT,
                command TEXT NOT NULL,
                output TEXT,
                status TEXT DEFAULT 'success',
                duration_ms INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "work_logs", "user_id", "INTEGER NOT NULL")
        _ensure_column(cur, "work_logs", "agent_id", "TEXT")
        _ensure_column(cur, "work_logs", "command", "TEXT NOT NULL")
        _ensure_column(cur, "work_logs", "output", "TEXT")
        _ensure_column(cur, "work_logs", "status", "TEXT DEFAULT 'success'")
        _ensure_column(cur, "work_logs", "duration_ms", "INTEGER")
        _ensure_column(cur, "work_logs", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

        # ========== 质量保障表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quality_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT,
                title TEXT NOT NULL,
                detail TEXT,
                severity TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                cleaned_at TEXT,
                assigned_to TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 解救任务表（旧表，保留兼容） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rescue_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL,
                difficulty TEXT DEFAULT 'medium',
                pet_level TEXT DEFAULT 'C',
                status TEXT DEFAULT 'available',
                rescued_by_user_id INTEGER,
                rescued_by_agent_id TEXT,
                rescued_at TEXT,
                assigned_agent_id TEXT,
                solution TEXT,
                verification_result TEXT,
                attempts INTEGER DEFAULT 0,
                status_detail TEXT,
                reused_from_kb_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (issue_id) REFERENCES quality_issues(id),
                FOREIGN KEY (rescued_by_user_id) REFERENCES users(id)
            )
        """)
        _ensure_column(cur, "rescue_tasks", "assigned_agent_id", "TEXT")
        _ensure_column(cur, "rescue_tasks", "solution", "TEXT")
        _ensure_column(cur, "rescue_tasks", "verification_result", "TEXT")
        _ensure_column(cur, "rescue_tasks", "attempts", "INTEGER DEFAULT 0")
        _ensure_column(cur, "rescue_tasks", "status_detail", "TEXT")
        _ensure_column(cur, "rescue_tasks", "reused_from_kb_id", "INTEGER")

        # ========== 云宠战役·地图任务表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS yunchong_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                issue_id INTEGER,
                title TEXT NOT NULL,
                detail TEXT,
                difficulty TEXT DEFAULT 'medium',
                pet_level TEXT DEFAULT 'C',
                status TEXT DEFAULT 'available',
                longitude REAL DEFAULT 0,
                latitude REAL DEFAULT 0,
                distance_meters INTEGER DEFAULT 0,
                energy_cost INTEGER DEFAULT 0,
                batch_id TEXT,
                refreshed_at TEXT,
                expires_at TEXT,
                rescued_at TEXT,
                rescued_by_agent_id TEXT,
                solution TEXT,
                verification_result TEXT,
                attempts INTEGER DEFAULT 0,
                reused_from_kb_id INTEGER,
                status_detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id),
                FOREIGN KEY (issue_id) REFERENCES quality_issues(id)
            )
        """)

        # ========== 云宠战役·用户刷新记录表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS yunchong_refresh_log (
                user_id INTEGER PRIMARY KEY,
                last_refresh_at TEXT,
                current_batch_id TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 云宠战役·官方助手使用记录 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS yunchong_official_agent_usage (
                user_id INTEGER PRIMARY KEY,
                used_today INTEGER DEFAULT 0,
                reset_date TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 云宠战役·雷达道具 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS yunchong_radar (
                user_id INTEGER PRIMARY KEY,
                expires_at TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 失败案例表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS failed_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                issue_id INTEGER,
                title TEXT,
                detail TEXT,
                solution TEXT,
                fail_reason TEXT,
                verification_result TEXT,
                severity TEXT,
                seed_triggered INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ========== 宠物表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                pet_name TEXT,
                rarity TEXT NOT NULL,
                camp TEXT NOT NULL,
                element TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                stage INTEGER DEFAULT 0,
                skill_slots INTEGER DEFAULT 1,
                current_skills TEXT,
                strength INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 0,
                defense INTEGER DEFAULT 0,
                is_listed INTEGER DEFAULT 0,
                source_task_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES users(id)
            )
        """)

        # ========== 游戏资源表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL,
                amount INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_user_id, resource_type),
                FOREIGN KEY (owner_user_id) REFERENCES users(id)
            )
        """)

        # ========== 基地设施表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS base_facilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER NOT NULL,
                facility_type TEXT NOT NULL,
                level INTEGER DEFAULT 0,
                captain_pet_id INTEGER,
                member_pet_ids TEXT,
                status TEXT DEFAULT 'idle',
                last_produced_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_user_id, facility_type),
                FOREIGN KEY (owner_user_id) REFERENCES users(id)
            )
        """)

        # ========== 官方算力服务目录 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS official_compute_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_key TEXT UNIQUE NOT NULL,
                service_name TEXT NOT NULL,
                description TEXT,
                unit_cost INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ========== 用户算力余额表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_compute_balance (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                total_purchased INTEGER DEFAULT 0,
                total_consumed INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 算力交易记录表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS compute_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tx_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                service_key TEXT,
                detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 初始化官方算力服务目录
        cur.execute("SELECT COUNT(*) as cnt FROM official_compute_services")
        if cur.fetchone()["cnt"] == 0:
            default_services = [
                ("multimodal_image", "多模态图像生成", "调用官方图像生成模型", 50),
                ("multimodal_audio", "音频合成", "调用官方音频合成模型", 30),
                ("cloud_finetune", "云端GPU微调", "使用官方GPU资源微调模型", 500),
                ("large_simulation", "大规模仿真", "使用官方算力运行复杂仿真", 200),
                ("vision_analysis", "高级视觉分析", "调用官方多模态模型分析图像", 20),
            ]
            for key, name, desc, cost in default_services:
                cur.execute("""
                    INSERT INTO official_compute_services
                    (service_key, service_name, description, unit_cost, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (key, name, desc, cost))

        # ========== 蜂群待处理任务表 ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS swarm_pending_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                conversation_id INTEGER,
                user_id INTEGER NOT NULL,
                commander_id TEXT,
                executor_id TEXT,
                user_text TEXT,
                steps TEXT,
                results TEXT,
                done_steps TEXT,
                retry_count INTEGER DEFAULT 0,
                is_draft INTEGER DEFAULT 0,
                cancelled INTEGER DEFAULT 0,
                no_plan INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # 加 supervisor_id 字段（v0.17.0）
        _ensure_column(cur, "swarm_pending_tasks", "supervisor_run_id", "INTEGER")
        _ensure_column(cur, "swarm_pending_tasks", "supervisor_id", "TEXT")


        # ========== 蜂群审核日志表（v0.15.0 从 swarm_service 收编） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS swarm_reviews (
                step_type TEXT,  -- v0.17.0 区分 command / harness

                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                conversation_id INTEGER,
                step_id INTEGER,
                command TEXT,
                exec_status TEXT,
                review_result TEXT,
                review_reason TEXT,
                output_preview TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # ========== 意图误判反馈表（v0.14.1 从 swarm_service 收编） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intent_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id TEXT,
                original_input TEXT NOT NULL,
                feedback_type TEXT NOT NULL DEFAULT 'false_positive',
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # ========== 经验库：交互模式表（v0.17.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS interaction_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL DEFAULT 'general',
                pattern_key TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                context_signature TEXT NOT NULL,
                role TEXT,
                evidence TEXT,
                confidence REAL DEFAULT 0.5,
                hit_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                distinct_user_count INTEGER DEFAULT 0,
                last_hit_at TEXT,
                last_success_at TEXT,
                status TEXT DEFAULT 'active',
                source_task_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_patterns_key_sig ON interaction_patterns(domain, pattern_key, context_signature)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_patterns_domain_type ON interaction_patterns(domain, pattern_type, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_patterns_updated ON interaction_patterns(updated_at)")

        # ========== 经验库：领域注册表（v0.17.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS domains (
                domain TEXT PRIMARY KEY,
                pattern_count INTEGER DEFAULT 0,
                active INTEGER DEFAULT 0,
                activated_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("INSERT OR IGNORE INTO domains (domain, active) VALUES ('dev', 0)")
        cur.execute("INSERT OR IGNORE INTO domains (domain, active) VALUES ('image', 0)")
        cur.execute("INSERT OR IGNORE INTO domains (domain, active) VALUES ('ecommerce', 0)")
        cur.execute("INSERT OR IGNORE INTO domains (domain, active) VALUES ('game', 0)")
        cur.execute("INSERT OR IGNORE INTO domains (domain, active) VALUES ('general', 1)")
        # ========== 项目库：分片表（v0.17.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                section_title TEXT,
                section_path TEXT,
                section_level INTEGER DEFAULT 2,
                chunk_index INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                embedding BLOB,
                content_hash TEXT,
                freshness_score REAL DEFAULT 1.0,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ensure_column(cur, "project_docs", "user_id", "INTEGER DEFAULT 0")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_pdocs_source ON project_docs(source_file)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pdocs_hash ON project_docs(content_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pdocs_status ON project_docs(status)")

        # ========== 项目库：源文件元数据表（v0.17.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_docs_meta (
                source_file TEXT PRIMARY KEY,
                source_version TEXT,
                chunk_count INTEGER DEFAULT 0,
                file_hash TEXT,
                imported_at TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # ========== 执行笔记表（v0.17.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS execution_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                user_id INTEGER,
                user_input TEXT NOT NULL,
                summary TEXT,
                outcome TEXT DEFAULT 'success',
                steps_digest TEXT,
                embedding BLOB,
                content_hash TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exnotes_hash ON execution_notes(content_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exnotes_task ON execution_notes(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exnotes_status ON execution_notes(status)")
        # ========== 附件表（v0.17.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                original_name TEXT,
                stored_path TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER DEFAULT 0,
                kind TEXT DEFAULT 'file',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_attach_user ON attachments(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_attach_fileid ON attachments(file_id)")

        # ========== 自主模式运行记录表（v0.18.0） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS supervisor_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                conversation_id INTEGER NOT NULL,
                supervisor_id TEXT,
                goal TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                current_round INTEGER DEFAULT 0,
                max_rounds INTEGER DEFAULT 5,
                credits_used INTEGER DEFAULT 0,
                history TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_suprun_user ON supervisor_runs(user_id)")
        _ensure_column(cur, "supervisor_runs", "task_type", "TEXT")


        # ========== 积分库（v0.20） ==========
        cur.execute("""
            CREATE TABLE IF NOT EXISTS credit_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                source TEXT,
                created_at TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_pool_time ON credit_pool(created_at)")


        # ========== 索引 ==========
        # 云宠战役
        cur.execute("CREATE INDEX IF NOT EXISTS idx_yunchong_owner_status ON yunchong_tasks(owner_user_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_yunchong_batch ON yunchong_tasks(batch_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_yunchong_expires ON yunchong_tasks(expires_at)")
        # 记忆库
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_task ON safety_memory(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_hash ON safety_memory(content_hash)")
        # 记忆库新增：按用户+类型检索（v0.16.0）
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_user_type ON safety_memory(user_id, memory_type)")
        # 蜂群待处理任务
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_pending_task ON swarm_pending_tasks(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_pending_status ON swarm_pending_tasks(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_pending_conv ON swarm_pending_tasks(conversation_id)")
        # 蜂群审核日志
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_task ON swarm_reviews(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_time ON swarm_reviews(created_at)")
        # 蜂群审核日志新增：按会话查询（v0.16.0）
        cur.execute("CREATE INDEX IF NOT EXISTS idx_swarm_reviews_conversation ON swarm_reviews(conversation_id)")

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
