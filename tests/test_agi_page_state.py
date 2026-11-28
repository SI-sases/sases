from agi.page_state import classify


def test_classify_upload_limit():
    out = classify("每日上传\n已达到上限", "https://studio.youtube.com/")
    assert out["state"] == "upload_limit"


def test_classify_login_and_normal():
    assert classify("扫码登录") ["state"] == "login_required"
    assert classify("视频投稿\n标题\n简介") ["state"] == "normal"
