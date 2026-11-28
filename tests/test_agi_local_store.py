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


def test_local_metrics(tmp_path, monkeypatch):
    db = tmp_path / "local_runtime.db"
    monkeypatch.setattr(local_store, "_path", lambda: db)
    local_store.set_metric("browser_wait_ms", 12.5)
    assert local_store.metrics()["browser_wait_ms"] == 12.5


def test_note_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(local_store, "_path", lambda: tmp_path / "local.db")
    assert local_store.note_attempt("a") == 1
    assert local_store.note_attempt("a") == 2
    local_store.clear_attempts("a")
    assert local_store.note_attempt("a") == 1
