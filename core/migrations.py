"""数据库迁移框架：按版本号顺序应用 schema 变更。"""
import datetime

SCHEMA_VERSION = 17


def _now_iso():
    return datetime.datetime.now().isoformat()


def _migrate_v1_outbox(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT UNIQUE NOT NULL, target_url TEXT NOT NULL, payload TEXT NOT NULL, headers TEXT, status TEXT NOT NULL DEFAULT 'pending', retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 5, next_retry_at TEXT NOT NULL, last_error TEXT, created_at TEXT NOT NULL, completed_at TEXT)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_due ON outbox(status, next_retry_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_msg ON outbox(msg_id)")


def _migrate_v2_hmac(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS auth_meta (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS nonce_cache (user_id INTEGER, nonce TEXT, expire_at TEXT, PRIMARY KEY (user_id, nonce))")


def _migrate_v3_reconcile(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS asset_snapshots (snapshot_date TEXT PRIMARY KEY, total_seed REAL NOT NULL, total_compute REAL NOT NULL, user_count INTEGER NOT NULL, tx_count INTEGER NOT NULL, ledger_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS reconcile_issues (id INTEGER PRIMARY KEY AUTOINCREMENT, issue_type TEXT NOT NULL, detail TEXT, detected_at TEXT NOT NULL, resolved INTEGER DEFAULT 0, resolved_at TEXT, resolved_by TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS user_frozen (user_id INTEGER PRIMARY KEY, reason TEXT, frozen_at TEXT, frozen_by TEXT DEFAULT 'system')")




def _migrate_v4_transfer_fields(cur):
    cur.execute("ALTER TABLE transactions ADD COLUMN idempotency_key TEXT")
    cur.execute("ALTER TABLE transactions ADD COLUMN sender_node_id TEXT")
    cur.execute("ALTER TABLE transactions ADD COLUMN receiver_node_id TEXT")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_idem ON transactions(idempotency_key) WHERE idempotency_key IS NOT NULL")



def _migrate_v5_credit_type(cur):
    cur.execute("PRAGMA table_info(transactions)")
    cols = [r[1] for r in cur.fetchall()]
    if "credit_type" not in cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN credit_type TEXT DEFAULT 'credits'")

def _ensure_col(cur, table, col, ddl):
    cur.execute("PRAGMA table_info(" + table + ")")
    cols = [r[1] for r in cur.fetchall()]
    if col not in cols:
        cur.execute("ALTER TABLE " + table + " ADD COLUMN " + col + " " + ddl)


def _migrate_v6_group_columns(cur):
    # 群红包/群任务在总结里声明过 packet_type，但基线表没有这一列
    _ensure_col(cur, "group_red_packets", "packet_type", "TEXT DEFAULT 'lucky'")
    _ensure_col(cur, "group_tasks", "packet_type", "TEXT DEFAULT 'lucky'")


def _migrate_v7_api_registry(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_registry'")
    if not cur.fetchone():
        return
    _ensure_col(cur, "api_registry", "tool_id", "TEXT")
    cur.execute("PRAGMA table_info(api_registry)")
    cols = [r[1] for r in cur.fetchall()]
    if "id" in cols:
        cur.execute("UPDATE api_registry SET tool_id='api_' || id WHERE tool_id IS NULL OR tool_id=''")
    elif "api_id" in cols:
        cur.execute("UPDATE api_registry SET tool_id='api_' || api_id WHERE tool_id IS NULL OR tool_id=''")


def _migrate_v8_legacy_columns(cur):
    """补齐旧库缺列；空表直接重建给 init_db 用新结构。"""
    def _exists(table):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        return cur.fetchone() is not None

    def _drop_empty(table):
        if not _exists(table):
            return
        cur.execute("SELECT COUNT(*) FROM " + table)
        if int(cur.fetchone()[0]) == 0:
            cur.execute("DROP TABLE " + table)

    _drop_empty("api_registry")
    _drop_empty("sync_received")

    _cols = {
        "conversations": [("active_task_id", "TEXT"), ("active_task_status", "TEXT"),
                          ("active_task_snapshot", "TEXT")],
        "license_keys": [("used_at", "TEXT"), ("used_by", "TEXT"), ("device_fp", "TEXT")],
        "supervisor_runs": [("task_fingerprint", "TEXT"), ("lease_owner", "TEXT"),
                            ("lease_until", "TEXT"), ("heartbeat_at", "TEXT"),
                            ("deadline_at", "TEXT")],
    }
    for table, cols in _cols.items():
        if not _exists(table):
            continue
        for name, typ in cols:
            _ensure_col(cur, table, name, typ)


def _migrate_v9_sync_received(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_received'")
    if not cur.fetchone():
        return
    for name, typ in (("source_node", "TEXT"), ("table_name", "TEXT"), ("record_id", "TEXT"),
                      ("hlc_ts", "TEXT"), ("payload", "TEXT"), ("applied", "INTEGER DEFAULT 0"),
                      ("created_at", "TEXT")):
        _ensure_col(cur, "sync_received", name, typ)


def _migrate_v10_agent_context(cur):
    for table, cols in {
        "agent_messages": [("compacted", "INTEGER DEFAULT 0")],
        "agent_summary": [("summary_message_id", "INTEGER"), ("tokens_before", "INTEGER"),
                          ("tokens_after", "INTEGER"), ("reason", "TEXT")],
    }.items():
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            continue
        for name, typ in cols:
            _ensure_col(cur, table, name, typ)


def _migrate_v11_agent_todos(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            run_id INTEGER NOT NULL DEFAULT 0,
            items_json TEXT NOT NULL,
            updated_at TEXT,
            UNIQUE (conversation_id, run_id)
        )
    """)


def _migrate_v12_agent_goals(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id INTEGER,
            goal TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            max_rounds INTEGER DEFAULT 10,
            rounds_done INTEGER DEFAULT 0,
            budget_tokens INTEGER DEFAULT 200000,
            next_run_at TEXT,
            last_run_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)


def _migrate_v13_node_identity(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS identity_nodes (
            node_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            profile TEXT NOT NULL,
            ed25519_pubkey TEXT NOT NULL,
            wg_pubkey TEXT,
            device_fingerprint TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            manifest_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            revoked_at TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_nodes_user ON identity_nodes(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_nodes_status ON identity_nodes(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_nodes_wg ON identity_nodes(wg_pubkey)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_identity_nodes_ed25519 ON identity_nodes(ed25519_pubkey)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS identity_creator_grants (
            grant_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            node_id TEXT NOT NULL,
            status TEXT NOT NULL,
            scopes TEXT NOT NULL,
            approved_by INTEGER,
            approved_at TEXT,
            expires_at TEXT,
            revoke_reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_grants_node ON identity_creator_grants(node_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_grants_status ON identity_creator_grants(status)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS identity_capabilities (
            node_id TEXT NOT NULL,
            capability TEXT NOT NULL,
            granted_by INTEGER,
            granted_at TEXT,
            expires_at TEXT,
            PRIMARY KEY (node_id, capability)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS identity_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            user_id INTEGER,
            profile TEXT,
            grant_id TEXT,
            capability TEXT,
            action TEXT NOT NULL,
            wg_peer_ip TEXT,
            device_fingerprint TEXT,
            result TEXT,
            detail TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_audit_node ON identity_audit(node_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_identity_audit_created ON identity_audit(created_at)")


def _migrate_v14_missing_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            cron_expr TEXT NOT NULL,
            timezone TEXT DEFAULT 'Asia/Shanghai',
            task_template TEXT NOT NULL,
            task_params TEXT,
            enabled INTEGER DEFAULT 1,
            missed_policy TEXT DEFAULT 'catch_up',
            failure_count INTEGER DEFAULT 0,
            paused_reason TEXT,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            is_active INTEGER DEFAULT 1,
            consecutive_failures INTEGER DEFAULT 0
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user ON scheduled_tasks(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next ON scheduled_tasks(next_run_at)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_api_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            api_name TEXT NOT NULL,
            api_desc TEXT,
            endpoint TEXT NOT NULL,
            method TEXT DEFAULT 'GET',
            auth_type TEXT DEFAULT 'none',
            auth_key_encrypted TEXT,
            auth_header_name TEXT DEFAULT 'Authorization',
            params_example TEXT,
            response_path TEXT,
            capability_tags TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_api_configs_user ON user_api_configs(user_id)")


def _migrate_v15_creator_review(cur):
    cur.execute("PRAGMA table_info(identity_creator_grants)")
    existing = {row[1] for row in cur.fetchall()}
    for name, definition in (
        ("application_note", "TEXT"),
        ("review_note", "TEXT"),
        ("reviewed_at", "TEXT"),
    ):
        if name not in existing:
            cur.execute(f"ALTER TABLE identity_creator_grants ADD COLUMN {name} {definition}")


def _migrate_v16_creator_portfolio(cur):
    cur.execute("PRAGMA table_info(identity_creator_grants)")
    existing = {row[1] for row in cur.fetchall()}
    if "portfolio_url" not in existing:
        cur.execute("ALTER TABLE identity_creator_grants ADD COLUMN portfolio_url TEXT")


def _migrate_v17_client_ops(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS client_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload TEXT,
            status TEXT DEFAULT 'pending',
            requested_by INTEGER,
            created_at TEXT,
            started_at TEXT,
            finished_at TEXT,
            result TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_ops_node_status ON client_operations(node_id, status)")


MIGRATIONS = {1: _migrate_v1_outbox, 2: _migrate_v2_hmac, 3: _migrate_v3_reconcile,
              4: _migrate_v4_transfer_fields, 5: _migrate_v5_credit_type,
              6: _migrate_v6_group_columns, 7: _migrate_v7_api_registry,
              8: _migrate_v8_legacy_columns, 9: _migrate_v9_sync_received,
              10: _migrate_v10_agent_context, 11: _migrate_v11_agent_todos,
              12: _migrate_v12_agent_goals, 13: _migrate_v13_node_identity,
              14: _migrate_v14_missing_tables, 15: _migrate_v15_creator_review,
              16: _migrate_v16_creator_portfolio, 17: _migrate_v17_client_ops}


def ensure_schema():
    from core.db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    with db_cursor() as cur:
        row = cur.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current = row[0] if row and row[0] is not None else 0
    for v in range(current + 1, SCHEMA_VERSION + 1):
        print(f"[migrate] applying v{v}")
        with db_cursor(commit=True) as cur:
            MIGRATIONS[v](cur)
            cur.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", (v, _now_iso()))
        print(f"[migrate] v{v} ok")
    print(f"[migrate] schema at v{SCHEMA_VERSION}")


def current_version(conn):
    """返回当前 schema 版本（供 /version 展示）。"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(version) FROM schema_version")
        row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0
