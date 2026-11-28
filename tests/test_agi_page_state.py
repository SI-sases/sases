from agi.page_state import classify


def test_classify_upload_limit():
    out = classify("每日上传\n已达到上限", "https://studio.youtube.com/")
    assert out["state"] == "upload_limit"


def test_classify_login_and_normal():
    assert classify("扫码登录") ["state"] == "login_required"
    assert classify("视频投稿\n标题\n简介") ["state"] == "normal"


def test_snapshot_cleanup(tmp_path):
    from agi import browser_snapshot
    base = tmp_path / "snapshots"; base.mkdir()
    old = base / "old.png"; old.write_bytes(b"x")
    new = base / "new.png"; new.write_bytes(b"y")
    import os
    os.utime(old, (1, 1))
    removed = browser_snapshot.cleanup(base, max_age_days=1)
    assert "old.png" in removed
    assert new.exists()


def test_snapshot_tool_registered():
    from agi.tools import build_default_registry
    reg = build_default_registry()
    assert reg.get("browser.snapshot").risk == "read"


def test_target_tools_registered():
    from agi.tools import build_default_registry
    reg = build_default_registry()
    assert reg.get("browser.click_target").risk == "write"
    assert reg.get("browser.fill_targets").risk == "write"


def test_wait_extract_upload_registered():
    from agi.tools import build_default_registry
    reg = build_default_registry()
    assert reg.get("browser.wait_for").risk == "read"
    assert reg.get("browser.extract").risk == "read"
    assert reg.get("browser.upload").risk == "write"


def test_recovery_observe_plan():
    from agi import browser_agent
    snap = {"state": "normal", "elements": [
        {"tag": "button", "text": "发布", "visible": True},
        {"tag": "input", "placeholder": "标题", "visible": True},
    ]}
    plan = browser_agent.plan(snap)
    assert plan["mode"] == "observe"
    assert plan["automatic"] is False
    assert plan["actions"]
