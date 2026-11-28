import sqlite3

from agi import notifications, platform_quota


def test_notifications(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    nid = notifications.create(conn, "child failed", conversation_id=9, severity="high")
    rows = notifications.list_after(conn, 0, 9)
    assert rows[0]["id"] == nid
    notifications.mark_read(conn, [nid])
    assert notifications.list_after(conn, 0, 9)[0]["read_at"] is not None
    conn.close()


def test_platform_quota(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    platform_quota.record(conn, "youtube", "upload limit")
    assert platform_quota.list_active(conn)[0]["platform"] == "youtube"
    conn.close()
