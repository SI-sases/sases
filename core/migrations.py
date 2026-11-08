"""数据库迁移框架：按版本号顺序应用 schema 变更。"""
import datetime

SCHEMA_VERSION = 5


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

MIGRATIONS = {1: _migrate_v1_outbox, 2: _migrate_v2_hmac, 3: _migrate_v3_reconcile, 4: _migrate_v4_transfer_fields, 5: _migrate_v5_credit_type}


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

def apply_migrations(cur):
    """接受外部游标，幂等地应用所有未应用的迁移（供 init_db 调用，不自己 commit）"""
    cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    cur.execute("SELECT MAX(version) FROM schema_version")
    row = cur.fetchone()
    current = row[0] if row and row[0] is not None else 0
    if current >= SCHEMA_VERSION:
        print(f"[migrate] schema 已在 v{current}，无需迁移")
        return
    for v in range(current + 1, SCHEMA_VERSION + 1):
        try:
            MIGRATIONS[v](cur)
        except Exception as e:
            err = str(e).lower()
            if "duplicate column" in err or "already exists" in err:
                print(f"[migrate] v{v} 已应用，跳过")
            else:
                print(f"[migrate] v{v} 失败: {e}")
                raise
        cur.execute("INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)", (v, _now_iso()))
        print(f"[migrate] v{v} ok")
