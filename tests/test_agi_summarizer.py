from agi.summarizer import summarize


def test_summarizer_fallback_keeps_constraints(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    out = summarize(["标题用 SASES 工作台", "先 dry-run，不要自动公开", "随便聊聊"], "发布视频")
    assert out["mode"] == "fallback"
    assert "SASES" in out["summary"]
    assert "dry-run" in out["summary"]
    assert "不要自动公开" in out["summary"]


def test_summarizer_empty():
    out = summarize([], "发布")
    assert out["mode"] == "empty"
