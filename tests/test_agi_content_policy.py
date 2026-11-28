from agi.content_policy import sanitize


def test_sanitize_removes_vendor_disclaimers():
    text = "SASES 自托管工作台。独立开源项目 · 非大厂官方产品。"
    out = sanitize(text)
    assert "非大厂" not in out
    assert "大厂官方" not in out
