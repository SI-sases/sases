from agi import conversation_extractor


def test_extract_generic_context():
    out = conversation_extractor.extract(
        "帮我把 data/demo.mp4 发到 YouTube，先 dry-run，不要自动公开，验收公开链接")
    assert any(f["key"] == "platform" and f["value"] == "youtube" for f in out["facts"])
    assert any(a["name"] == "demo.mp4" for a in out["artifacts"])
    assert any("dry-run" in c for c in out["constraints"])
    assert "不要自动公开" in out["constraints"]
    assert "公开链接" in out["acceptance"]
