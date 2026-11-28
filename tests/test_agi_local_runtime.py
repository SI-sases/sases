import time
from pathlib import Path

from agi import local_runtime


def test_runtime_starts_local_agent(monkeypatch):
    calls = []
    agent = {"agent_id": "a1", "node_id": "local", "status": "queued", "goal": "policy",
             "task_json": '{"steps":[{"tool":"platform.policy","args":{}}]}'}

    def fake(server, token, method, path, body=None):
        calls.append((method, path))
        if method == "GET" and path == "/approvals/approved":
            return {"approvals": []}
        if method == "GET" and path == "/agents":
            return {"agents": [agent]}
        if method == "POST" and path.endswith("/claim"):
            return {"ok": True}
        return {"ok": True}

    monkeypatch.setattr(local_runtime, "_call", fake)
    monkeypatch.setattr(local_runtime, "_read_only", lambda reg, steps: (True, ""))
    monkeypatch.setattr(local_runtime, "_execute", lambda *a, **k: {"ok": True})
    rt = local_runtime.LocalRuntime("http://x", "t", 2, lock_port=0)
    result = rt.poll()
    assert result["started"] == "a1"
    for _ in range(30):
        if not rt.active:
            break
        time.sleep(0.05)
    assert "a1" not in rt.active
    assert rt._is_browser([{"tool": "adapter.run"}]) is True


def test_checkpoint_cleanup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ck = Path("data/checkpoints"); ck.mkdir(parents=True)
    (ck / "keep.json").write_text("{}", encoding="utf-8")
    (ck / "stale.json").write_text("{}", encoding="utf-8")
    import os
    old = 1
    os.utime(ck / "stale.json", (old, old))
    rt = local_runtime.LocalRuntime("http://x", "t", 1, lock_port=0)
    removed = rt.cleanup_checkpoints({"keep"}, max_age=3600)
    assert "stale.json" in removed
    assert (ck / "keep.json").exists()
