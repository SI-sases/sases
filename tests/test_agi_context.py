import sqlite3

from agi.context import compact
from agi.lessons import record, search


def test_context_compact_keeps_errors():
    text = compact([
        {"node_id": "node-C", "severity": "error", "message": "task timeout"},
        {"node_id": "node-B", "severity": "info", "message": "ok"},
    ])
    assert "events: 2" in text
    assert "task timeout" in text


def test_lessons_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    record(conn, "cloudflare blocked", "cancel task", "cancelled", "node-C")
    assert search(conn, "cloudflare")[0]["action"] == "cancel task"
    conn.close()
