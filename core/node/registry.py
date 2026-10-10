"""core/hive/registry.py —— 节点注册表 CRUD。

每个节点本地都有一份 node_registry，记录已知的其他节点。
"""


def upsert_node(node_id, public_key, url, role):
    from core.db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO node_registry (node_id, public_key, url, role, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(node_id) DO UPDATE SET
                public_key = excluded.public_key,
                url = excluded.url,
                role = excluded.role,
                last_seen = CURRENT_TIMESTAMP
        """, (node_id, public_key, url, role))


def get_node(node_id):
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT node_id, public_key, url, role, status, first_seen, last_seen "
            "FROM node_registry WHERE node_id=?",
            (node_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip(['node_id', 'public_key', 'url', 'role', 'status', 'first_seen', 'last_seen'], row))
    finally:
        conn.close()


def list_nodes(status='active'):
    from core.db import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT node_id, public_key, url, role, status, first_seen, last_seen "
            "FROM node_registry WHERE status=? ORDER BY node_id",
            (status,),
        )
        rows = cur.fetchall()
        return [
            dict(zip(['node_id', 'public_key', 'url', 'role', 'status', 'first_seen', 'last_seen'], r))
            for r in rows
        ]
    finally:
        conn.close()


def touch_node(node_id):
    from core.db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE node_registry SET last_seen=CURRENT_TIMESTAMP WHERE node_id=?",
            (node_id,),
        )


def remove_node(node_id):
    from core.db import db_cursor
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM node_registry WHERE node_id=?", (node_id,))
