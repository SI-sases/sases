from agi import local_outbox


def test_outbox_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(local_outbox, "_path", lambda: tmp_path / "outbox.db")
    rid = local_outbox.add("a1", "done", {"ok": True})
    rows = local_outbox.pending()
    assert rows[0]["agent_id"] == "a1"
    assert rows[0]["result"]["ok"] is True
    local_outbox.remove(rid)
    assert local_outbox.pending() == []


def test_finish_failure_goes_to_outbox(tmp_path, monkeypatch):
    from agi import local_worker
    monkeypatch.setattr(local_outbox, "_path", lambda: tmp_path / "outbox.db")
    def fake(server, token, method, path, body=None):
        if path.endswith("/finish"):
            raise RuntimeError("offline")
        return {"ok": True}
    monkeypatch.setattr(local_worker, "_call", fake)
    steps = [{"tool": "platform.policy", "args": {"url": "https://www.reddit.com/", "action": "open_for_human"}}]
    out = local_worker._execute("http://x", "t", __import__("agi.tools", fromlist=["build_default_registry"]).build_default_registry(), "a1", steps, "policy")
    assert out["result"].get("outboxed") is True
    assert local_outbox.pending()[0]["agent_id"] == "a1"
