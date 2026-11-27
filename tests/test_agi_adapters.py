from agi import adapters


def test_adapter_registry_marks_unimplemented():
    rows = {a["id"]: a for a in adapters.list_adapters()}
    assert rows["reddit"]["implemented"] is True
    assert rows["xiaohongshu"]["mode"] == "manual"
    assert rows["douyin"]["implemented"] is False


def test_manual_adapter_refuses():
    result = adapters.run("xiaohongshu", {})
    assert result["ok"] is False
    assert result["error"] == "adapter_not_implemented"
