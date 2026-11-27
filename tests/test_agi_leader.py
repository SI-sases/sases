import sqlite3

from agi import leader


def test_leader_lock_excludes_second_owner(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    assert leader.acquire(conn, "fleet", "sz", 60) is True
    assert leader.acquire(conn, "fleet", "local", 60) is False
    assert leader.renew(conn, "fleet", "sz", 60) is True
    assert leader.release(conn, "fleet", "sz") is True
    assert leader.acquire(conn, "fleet", "local", 60) is True
    conn.close()
