from agi import shell_tools


def test_shell_allowlist_and_pwd():
    assert shell_tools.run({"command": "pwd"})["ok"] is True
    assert shell_tools.run({"command": "git status --short"})["ok"] is True
    assert shell_tools.run({"command": "rm -rf /"})["ok"] is False
    assert shell_tools.run({"command": "git config --global user.name x"})["ok"] is False


def test_shell_write_requires_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("SASES_FS_ROOT", str(tmp_path))
    monkeypatch.setenv("SASES_AGI_DB", str(tmp_path / "agi.db"))
    assert shell_tools.run_write({"command": "mkdir d"})["error"] == "approval_required"
    assert shell_tools.run_write({"command": "mkdir d", "_approved": True})["ok"]
    assert (tmp_path / "d").is_dir()
