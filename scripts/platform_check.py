#!/usr/bin/env python3
"""Check platform login state through the local Edge CDP session."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

CDP = os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222")
PLATFORMS = {
    "xiaohongshu": "https://creator.xiaohongshu.com/new/note-manager",
    "douyin": "https://creator.douyin.com/creator-micro/content/upload",
    "medium": "https://medium.com/new-story",
    "linkedin": "https://www.linkedin.com/feed/",
    "blogger": "https://www.blogger.com/u/1/blog/posts/7227324231931786018",
    "github": "https://github.com/SI-sases/sases",
    "gitcn": "https://forum.github-zh.cn",
}
LOGIN_MARKERS = ("/login", "signin", "accounts.google.com", "passport", "登录")


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
                page.wait_for_timeout(2000)
                results[name] = {
                    "status": classify(name, page.url, page.title()),
                    "url": page.url,
                    "title": page.title(),
                }
            except Exception as exc:
                results[name] = {
                    "status": "error",
                    "url": page.url,
                    "error": f"{type(exc).__name__}: {str(exc)[:160]}",
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
