import json

from agi import local_runtime


def test_platform_fallback_spawns_bilibili(monkeypatch):
    monkeypatch.setenv("SASES_AUTO_PLATFORM_FALLBACK", "1")
    calls = []

    def fake_call(server, token, method, path, body=None):
        calls.append((path, body or {}))
        if path == "/agents/spawn":
            return {"ok": True, "agent_id": "fallback-agent"}
        return {"ok": True}

    monkeypatch.setattr(local_runtime, "_call", fake_call)
    rt = local_runtime.LocalRuntime("http://x", "t", lock_port=0)
    steps = [{"tool": "adapter.run", "args": {
        "adapter": "youtube", "args": {"dry_run": True, "video": "x.mp4"}}}]
    inner = rt._platform_fallback(
        {"agent_id": "a1", "name": "publish", "node_id": "local"},
        {"fallback_depth": 0}, steps, "platform_limit: upload limit", {}, "publish",
    )
    assert inner["fallback_agent_id"] == "fallback-agent"
    assert inner["fallback_platform"] == "bilibili"
    spawn = next(body for path, body in calls if path == "/agents/spawn")
    assert spawn["task"]["steps"][0]["args"]["adapter"] == "bilibili"
