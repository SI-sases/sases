from agi import local_bridge


def test_local_bridge_polls_agent(monkeypatch):
    calls = []

    def fake_call(method, path, body=None):
        calls.append((method, path))
        if path == "/agents/spawn":
            return {"ok": True, "agent_id": "local-a"}
        return {"agent": {"status": "done", "result_json": '{"ok": true, "text": "local"}'}}

    monkeypatch.setattr(local_bridge, "_call", fake_call)
    out = local_bridge.run_readonly("fs.read", {"path": "README.md"}, timeout=5)
    assert out["ok"] is True
    assert out["text"] == "local"
    assert out["local_agent_id"] == "local-a"


def test_local_write_start(monkeypatch):
    monkeypatch.setattr(local_bridge, "_call", lambda *a, **k: {"ok": True, "agent_id": "w1"})
    out = local_bridge.start("fs.write", {"path": "x", "content": "y"})
    assert out["ok"] is True and out["agent_id"] == "w1"
    assert out["requires_local_approval"] is True
