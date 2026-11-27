import sqlite3

from agi.policy import classify
from agi import escalation


def test_policy_routes_routine_to_main_and_high_risk_to_human():
    assert classify("health.observe", "info")["owner"] == "main"
    assert classify("deploy.promote", "info")["owner"] == "human"
    assert classify("event.record", "critical")["owner"] == "human"


def test_escalation_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    eid = escalation.create(conn, "node-C", "disk full", "high")
    assert escalation.list_open(conn)[0]["id"] == eid
    assert escalation.resolve(conn, eid) is True
    assert escalation.list_open(conn) == []
    conn.close()
