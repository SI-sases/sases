import sqlite3

from agi import agent_trace


def test_agent_trace_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    agent_trace.add(conn, "a1", 1, "step", "fs.read", {"path": "x"}, {"ok": True})
    agent_trace.add(conn, "a1", 2, "step", "fs.grep", {"pattern": "y"}, {"ok": False})
    rows = agent_trace.list_for(conn, "a1")
    assert [r["seq"] for r in rows] == [1, 2]
    assert rows[0]["tool"] == "fs.read"
    conn.close()
