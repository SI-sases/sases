from agi.ask import answer


def test_ask_status_returns_markdown(tmp_path):
    from agi.runtime import ensure_schema
    db = str(tmp_path / "agi.db")
    ensure_schema(db)
    out = answer("帮我看看深圳、杭州、香港现在什么情况", db)
    assert out["intent"] == "status"
    assert out["markdown"].startswith("# SASES 主 AGI 汇报")


def test_ask_publish_is_not_automatic(tmp_path):
    out = answer("帮我发布到小红书", str(tmp_path / "agi.db"))
    assert out["intent"] == "publish"
    assert "不会直接提交" in out["markdown"]


def test_ask_refund_routes_human(tmp_path):
    out = answer("我要退款", str(tmp_path / "agi.db"))
    assert out["intent"] == "support"
    assert "人工" in out["markdown"]
