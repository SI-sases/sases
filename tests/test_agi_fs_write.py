from agi.tools import build_default_registry


def test_write_requires_approval_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    reg = build_default_registry()
    out = reg.invoke("main", "fs.write", {"path": "a.txt", "content": "hello"})
    assert out["ok"] is False and out["error"] == "approval_required"
    out = reg.invoke("main", "fs.write", {"path": "a.txt", "content": "hello", "_approved": True})
    assert out["ok"] is True
    out = reg.invoke("main", "fs.edit", {"path": "a.txt", "old": "hello", "new": "bye", "_approved": True})
    assert out["ok"] is True
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "bye"
