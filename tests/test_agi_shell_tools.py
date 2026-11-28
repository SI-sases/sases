from agi import shell_tools


def test_shell_allowlist_and_pwd():
    assert shell_tools.run({"command": "pwd"})["ok"] is True
    assert shell_tools.run({"command": "git status --short"})["ok"] is True
    assert shell_tools.run({"command": "rm -rf /"})["ok"] is False
    assert shell_tools.run({"command": "git config --global user.name x"})["ok"] is False
