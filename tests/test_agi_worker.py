import sqlite3

from agi import agents
from agi.tools import build_default_registry
from agi.worker import run_once


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
    conn.close()
