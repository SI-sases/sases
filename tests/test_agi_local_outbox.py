from agi import local_outbox


def test_outbox_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(local_outbox, "_path", lambda: tmp_path / "outbox.db")
    rid = local_outbox.add("a1", "done", {"ok": True})
    rows = local_outbox.pending()
    assert rows[0]["agent_id"] == "a1"
    assert rows[0]["result"]["ok"] is True
    local_outbox.remove(rid)
    assert local_outbox.pending() == []
