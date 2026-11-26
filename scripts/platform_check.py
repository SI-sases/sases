#!/usr/bin/env python3
"""Check platform login state through the local Edge CDP session."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

CDP = os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222")
PLATFORMS = {
    "xiaohongshu": "https://creator.xiaohongshu.com/publish/publish",
    "douyin": "https://creator.douyin.com/creator-micro/content/upload",
    "github": "https://github.com/SI-sases/sases",
    "x": "https://x.com/i88033",
    "tiktok": "https://www.tiktok.com/@sases_ai",
    "blogger": "https://www.blogger.com/u/1/blog/posts/7227324231931786018",
}
LOGIN_MARKERS = ("/login", "signin", "accounts.google.com", "passport", "登录")
AUTH_COOKIES = {
    "xiaohongshu": ("web_session",),
    "douyin": ("sessionid", "sessionid_ss", "sid_guard"),
    "github": ("user_session", "logged_in"),
    "x": ("auth_token",),
    "tiktok": ("sessionid", "sessionid_ss", "sid_guard"),
    "blogger": ("SID", "HSID", "SSID"),
}


def has_auth_cookie(context, platform: str, url: str) -> bool:
    try:
        names = {c["name"] for c in context.cookies(url)}
    except Exception:
        return False
    return any(name in names for name in AUTH_COOKIES.get(platform, ()))


def classify(platform: str, url: str, title: str) -> str:
    value = (url + " " + title).lower()
    if any(marker.lower() in value for marker in LOGIN_MARKERS):
        return "needs_login"
    if platform == "douyin" and "creator.douyin.com" not in url:
        return "needs_login"
    if platform == "medium" and "medium.com" not in url:
        return "needs_login"
    if platform == "linkedin" and "linkedin.com" not in url:
        return "needs_login"
    if platform == "blogger" and "/about" in url:
        return "needs_login"
    return "logged_in"


REPAIR = {
    "xiaohongshu": "打开小红书 App 扫码登录；再打开 creator.xiaohongshu.com/publish/publish；仍空白则换普通 Edge 登录后重试。",
    "douyin": "打开抖音 App 扫码登录；再打开 creator.douyin.com；一直“加载中”时关闭标签、清缓存、重新登录。",
    "tiktok": "确认已登录 TikTok；打开 tiktok.com/tiktokstudio/upload；空白时重新登录。",
    "github": "确认 GitHub 已登录；打开仓库页。",
    "x": "确认 X 已登录；打开个人页。",
    "blogger": "确认 Google 账号已登录；打开 Blogger 博文页。",
}


def diagnose(platform: str, status: str, body: str, body_len: int) -> dict:
    text = (body or "").lower()
    if status == "needs_login":
        return {"reason": "needs_login", "next_action": REPAIR.get(platform, "重新登录")}
    if status == "error":
        return {"reason": "cdp_or_page_error", "next_action": "检查 Edge CDP 9222 是否在运行，再重试。"}
    if any(x in text for x in ("验证", "滑动", "安全验证", "captcha", "verify")):
        return {"reason": "anti_bot", "next_action": "人工完成验证；不要连续刷新。"}
    if status == "page_error":
        return {"reason": "page_blank", "next_action": REPAIR.get(platform, "重新登录并刷新")}
    if body_len < 20:
        return {"reason": "empty_body", "next_action": REPAIR.get(platform, "重新登录并刷新")}
    return {"reason": "ok", "next_action": ""}


def main() -> int:
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parent.parent
    out_path = root / "data" / "platform_check.json"
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        for name, url in PLATFORMS.items():
            page = context.new_page()
            try:
                page.goto(url, wait_until="commit", timeout=20000)
                # Creator SPAs (XHS/Douyin/TikTok) often need >10s to render.
                page.wait_for_timeout(15000 if name in ("xiaohongshu", "douyin", "tiktok") else 4000)
                body = ""
                body_len = 0
                try:
                    body = page.locator("body").inner_text()
                    body_len = len(body)
                except Exception:
                    pass
                status = classify(name, page.url, page.title())
                auth = has_auth_cookie(context, name, url)
                if not auth:
                    status = "needs_login"
                elif any(marker in body for marker in ("重新登录", "无法打开", "页面暂时")):
                    status = "needs_login"
                elif body_len < 20 and name in ("douyin", "xiaohongshu") and "login" not in page.url.lower():
                    status = "page_error"
                results[name] = {
                    "status": status,
                    "url": page.url,
                    "title": page.title(),
                    "body_len": body_len,
                    **diagnose(name, status, body, body_len),
                }
            except Exception as exc:
                results[name] = {
                    "status": "error",
                    "url": page.url,
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                    "reason": "cdp_or_page_error",
                    "next_action": "检查 Edge CDP 9222 是否在运行，再重试。",
                }
            finally:
                page.close()
        browser.close()
    payload = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "cdp": CDP, "platforms": results}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
