from pathlib import Path

from agi import fs_tools, web_tools
from agi.tools import build_default_registry


def test_fs_read_list_grep_and_secret_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    (tmp_path / "README.md").write_text("SASES local runtime\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "agi.token").write_text("secret", encoding="utf-8")
    reg = build_default_registry()
    assert reg.invoke("main", "fs.list", {"path": "."})["ok"]
    assert reg.invoke("main", "fs.read", {"path": "README.md"})["text"].startswith("SASES")
    assert reg.invoke("main", "fs.grep", {"pattern": "runtime", "path": "."})["ok"]
    denied = reg.invoke("main", "fs.read", {"path": "data/agi.token"})
    assert denied["ok"] is False
    assert "sensitive" in denied["error"]


def test_web_rejects_private_urls():
    for url in ("http://127.0.0.1/", "http://localhost/", "file:///etc/passwd"):
        out = web_tools.fetch({"url": url})
        assert out["ok"] is False
