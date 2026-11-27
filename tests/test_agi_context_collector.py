import sqlite3

from agi import context_builder, context_collector


def test_collector_inherits_previous_context(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    first = context_builder.build(
        conn, "发布 YouTube",
        conversation_id=9,
        facts=[{"key": "platform", "value": "youtube"}],
        artifacts=[{"id": "a1", "uri": "file:///v.mp4", "name": "v.mp4"}],
        constraints=["先 dry-run"],
        history_summary="上次只差公开",
    )
    collected = context_collector.collect(conn, "继续 YouTube", 9)
    assert collected["used_conversation"] is True
    assert collected["facts"][0]["key"] == "platform"
    assert collected["artifacts"][0]["id"] == "a1"
    assert "先 dry-run" in collected["constraints"]
    second = context_builder.build(
        conn, "继续 YouTube", conversation_id=9,
        facts=collected["facts"], artifacts=collected["artifacts"],
        constraints=collected["constraints"], history_summary=collected["history_summary"],
    )
    assert second["context_id"] != first["context_id"]
    assert second["facts"] >= 1
    conn.close()
