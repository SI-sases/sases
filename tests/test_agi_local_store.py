from agi import local_store


def test_local_session_resume(tmp_path, monkeypatch):
    db = tmp_path / "local_runtime.db"
    monkeypatch.setattr(local_store, "_path", lambda: db)
    steps = [{"tool": "a"}, {"tool": "b"}]
    assert local_store.start("a1", "goal", steps) == 0
    local_store.step("a1", 1)
    assert local_store.start("a1", "goal", steps) == 1
    local_store.finish("a1", "done")
    assert local_store.start("a1", "goal", steps) == 0
