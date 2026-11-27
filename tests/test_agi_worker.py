import sqlite3

from agi import agents, approvals
from agi.tools import ToolRegistry, ToolSpec, build_default_registry
from agi.worker import run_once, status


def test_worker_claims_and_finishes(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    aid = agents.spawn(conn, "local", {"steps": [
        {"tool": "platform.policy", "args": {"url": "https://www.reddit.com/", "action": "open_for_human"}}
    ]}, name="policy", goal="policy", status="queued")
    result = run_once(conn, build_default_registry(), "test")
    assert result["claimed"] is True
    assert result["status"] == "done"
    assert agents.get_agent(conn, aid)["status"] == "done"
    assert status(conn)[0]["owner"] == "test"
    conn.close()


def test_worker_waits_for_approval_then_executes(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    reg = ToolRegistry()
    reg.register(ToolSpec("write.echo", lambda a: {"ok": True, "approved": bool(a.get("approved"))},
                          "write", frozenset({"main", "sub"})))
    aid = agents.spawn(conn, "node-C", {"steps": [{"tool": "write.echo", "args": {}}]},
                       name="write", goal="write", status="queued")
    first = run_once(conn, reg, "test")
    assert first["status"] == "needs_approval"
    approval_id = first["approval_id"]
    assert approvals.decide(conn, approval_id, "allow") is True
    second = run_once(conn, reg, "test")
    assert second["approved"] is True
    assert second["status"] == "done"
    assert agents.get_agent(conn, aid)["status"] == "done"
    conn.close()
