def test_workflow_read_only_and_limits(monkeypatch, tmp_path):
    from agi.tools import build_default_registry
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    reg = build_default_registry()
    out = reg.invoke("main", "workflow.run", {"steps": [
        {"tool": "fs.list", "args": {"path": "."}},
        {"tool": "fs.read", "args": {"path": "a.txt"}},
    ]})
    assert out["ok"] is True
    assert "hello" in str(out["results"][1]["result"])
    bad = reg.invoke("main", "workflow.run", {"steps": [{"tool": "fs.write", "args": {}}]})
    assert bad["ok"] is False
