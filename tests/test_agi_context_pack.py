import sqlite3

from agi import context_pack


def test_context_build_patch_fork(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    ctx = context_pack.create(conn, "publish video", scope={"conversation_id": 1},
                              acceptance=["public url"], constraints=["dry-run first"],
                              artifacts=[{"id": "a1", "uri": "file:///v.mp4"}])
    pack = context_pack.get(conn, ctx)
    assert pack["goal"] == "publish video"
    assert context_pack.render(conn, ctx)["text"].find("dry-run") != -1
    assert context_pack.patch(conn, ctx, {"facts": [{"key": "platform", "value": "youtube"}]})
    assert context_pack.get(conn, ctx)["version"] == 2
    child = context_pack.fork(conn, ctx)
    assert child != ctx
    assert context_pack.get(conn, child)["parent_context_id"] == ctx
    conn.close()
