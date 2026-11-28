from agi.context_compaction import compact_text


def test_compact_text_saves_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("SASES_CONTEXT_DIR", str(tmp_path))
    text = "A" * 10000 + "TAIL"
    out = compact_text(text, max_head=100, max_tail=20)
    assert out["compacted"] is True
    assert out["head"] == "A" * 100
    assert out["artifact"].endswith(".txt")
    assert (tmp_path / out["artifact"].split("\\")[-1]).exists()
