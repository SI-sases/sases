import json
import sqlite3

from agi import agents, escalation, monitor


def test_monitor_classifies_platform_limit(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    aid = agents.spawn(conn, "local", {"goal": "youtube"}, name="youtube", goal="youtube")
    agents.finish(conn, aid, "failed", {"ok": False, "error": "upload limit reached"})
    created = monitor.scan(conn)
    assert created
    assert "platform_limit" in created[0]["reason"]
    assert monitor.scan(conn) == []
    assert len(escalation.list_open(conn)) == 1
    conn.close()
