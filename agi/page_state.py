"""Classify a browser page into a small, actionable state."""
from __future__ import annotations

LIMIT = ("每日上传", "上传上限", "上传次数", "达到上限", "quota", "upload limit", "limit reached")
LOGIN = ("扫码登录", "登录失效", "请登录", "登录后", "sign in", "log in", "logged out")
CHALLENGE = ("人机验证", "安全验证", "验证码", "captcha", "challenge", "verify you are human")
PERMISSION = ("无权限", "没有权限", "禁止访问", "403", "forbidden", "permission denied")
PUBLISHED = ("发布成功", "已发布", "投稿成功", "published")


def classify(text: str, url: str = "", title: str = "") -> dict:
    hay = f"{title}\n{text}\n{url}".lower()

    def hit(words):
        return next((w for w in words if w.lower() in hay), "")

    for state, words in (
        ("upload_limit", LIMIT),
        ("login_required", LOGIN),
        ("captcha_or_challenge", CHALLENGE),
        ("permission_denied", PERMISSION),
        ("published", PUBLISHED),
    ):
        found = hit(words)
        if found:
            return {"state": state, "reason": found}
    return {"state": "normal", "reason": ""}
