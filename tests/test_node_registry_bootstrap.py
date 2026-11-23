import sqlite3

from core import db
from core.node_registry import NodeRegistry


def test_node_registry_creates_space_nodes_on_empty_db(tmp_path, monkeypatch):
    db_path = tmp_path / "empty.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    NodeRegistry()
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='space_nodes'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
