from agi import subagent_tools


def test_subagent_tools_wrap_agents_api(monkeypatch):
    calls = []

    def fake_call(method, path, body=None):
        calls.append((method, path))
        if path == "/agents/spawn":
            return {"ok": True, "agent_id": "a1"}
        if "/wait" in path:
            return {"ok": True, "agent": {"status": "done"}}
        return {"ok": True}

    monkeypatch.setattr(subagent_tools, "_call", fake_call)
    assert subagent_tools.spawn({"goal": "x", "steps": [{"tool": "fs.list"}]})["agent_id"] == "a1"
    assert subagent_tools.wait({"agent_id": "a1", "timeout": 5})["ok"] is True
    assert subagent_tools.message({"agent_id": "a1", "message": "go"})["ok"] is True
    assert subagent_tools.cancel({"agent_id": "a1"})["ok"] is True
    assert subagent_tools.trace({"agent_id": "a1"})["ok"] is True
    assert calls[0][0] == "POST" and calls[0][1] == "/agents/spawn"
