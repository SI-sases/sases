import os

from scripts import browser_checkpoint


def test_checkpoint_roundtrip(tmp_path, monkeypatch):
    p = tmp_path / "ckpt.json"
    monkeypatch.setenv("SASES_CHECKPOINT_FILE", str(p))
    browser_checkpoint.save("filled")
    assert browser_checkpoint.load()["phase"] == "filled"
    browser_checkpoint.clear()
    assert browser_checkpoint.load() == {}
