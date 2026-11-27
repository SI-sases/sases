from agi import local_worker
from agi.tools import build_default_registry


def test_local_worker_claims_local_agent(monkeypatch):
    calls = []
    agent = {
        "agent_id": "a1", "node_id": "local", "status": "queued", "goal": "policy",
        "task_json": '{"steps":[{"tool":"platform.policy","args":{"url":"https://www.reddit.com/","action":"open_for_human"}}]}',
    }

    def fake(server, token, method, path, body=None):
        calls.append((method, path, body))
        if method == "GET" and path == "/agents":
            return {"agents": [agent]}
        return {"ok": True}

    monkeypatch.setattr(local_worker, "_call", fake)
    result = local_worker.run_once("http://example", "token", build_default_registry())
    assert result["claimed"] is True
    assert result["status"] == "done"
    assert any(c[1].endswith("/finish") for c in calls)
