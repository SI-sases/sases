import sqlite3

import pytest

from agi.protocol import make_message
from agi.runtime import MainAGI
from agi.tools import ToolRegistry, ToolSpec


def test_message_validation():
    msg = make_message("agi.event", "node-A", severity="error", payload={"message": "x"})
    assert msg.to_dict()["node_id"] == "node-A"
    with pytest.raises(ValueError):
        make_message("bad.type", "node-A")


def test_profile_filtering():
    reg = ToolRegistry()
    reg.register(ToolSpec("read.only", lambda args: {"ok": True}, "read", frozenset({"main", "sub"})))
    assert [t.id for t in reg.for_profile("main")] == ["read.only"]
    with pytest.raises(PermissionError):
        reg.invoke("viewer", "read.only")


def test_runtime_records_health(tmp_path):
    db = str(tmp_path / "agi.db")
    reg = ToolRegistry()
    reg.register(ToolSpec("node.health", lambda args: {"ok": True, "data": {"ok": True, "node_id": "local"}},
                          "read", frozenset({"main", "sub"})))
    reg.register(ToolSpec("node.version", lambda args: {"ok": True, "data": {"commit": "abc"}},
                          "read", frozenset({"main", "sub"})))
    result = MainAGI(base_url="http://example.invalid", db_path=db, registry=reg).run_once()
    assert result["ok"] is True
    with sqlite3.connect(db) as conn:
        assert conn.execute("select count(*) from agi_events").fetchone()[0] == 1
        assert conn.execute("select health from agi_nodes where node_id='local'").fetchone()[0] == "ok"
