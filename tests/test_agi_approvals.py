import sqlite3

from agi import approvals


def test_approval_queue(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    aid = approvals.create(conn, "deploy.promote", {"version": "hq32"}, "promote", "high")
    assert approvals.list_pending(conn)[0]["tool"] == "deploy.promote"
    assert approvals.decide(conn, aid, "allow", "commander") is True
    assert approvals.list_pending(conn) == []
    conn.close()
