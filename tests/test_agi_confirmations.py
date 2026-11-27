import sqlite3

from agi import confirmations


def test_confirmation_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    cid = confirmations.create(conn, 777, "publish", ["auto", "no auto"], ["allow", "dry_run"])
    p = confirmations.pending(conn, 777)
    assert p["id"] == cid
    assert p["goal"] == "publish"
    assert confirmations.resolve(conn, cid, "allow") is True
    assert confirmations.pending(conn, 777) is None
    conn.close()
