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
    from agi import notifications
    assert notifications.list_after(conn, 0)[0]["message"].startswith("⚠️")
    conn.close()


def test_quota_recovery_requeues_agent(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    from agi import platform_quota
    platform_quota.record(conn, "youtube", "limit", hours=0)
    aid = agents.spawn(conn, "local", {"steps": [
        {"tool": "adapter.run", "args": {"adapter": "youtube"}}
    ]}, name="quota", goal="quota", status="quota_blocked")
    monitor.scan(conn)
    assert agents.get_agent(conn, aid)["status"] == "queued"
    conn.close()
