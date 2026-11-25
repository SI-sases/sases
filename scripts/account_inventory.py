#!/usr/bin/env python3
"""Collect public profile data from logged-in platforms through Edge CDP."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

CDP = os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222")
TARGETS = {
    "xiaohongshu": "https://www.xiaohongshu.com/user/profile/63eafd940000000026005a6a",
    "douyin": "https://www.douyin.com/user/self",
    "github": "https://github.com/SI-sases",
    "x": "https://x.com/i88033",
    "tiktok": "https://www.tiktok.com/",
    "blogger": "https://www.blogger.com/",
}


def main() -> int:
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parent.parent
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        for name, url in TARGETS.items():
            page = context.new_page()
            try:
                page.goto(url, wait_until="commit", timeout=25000)
                page.wait_for_timeout(3500)
                if name == "tiktok":
                    href = page.evaluate(
                        "() => { const a=[...document.querySelectorAll('a[href^=\"/@\"]')][0]; return a ? a.getAttribute('href') : null; }"
                    )
                    if href:
                        page.goto("https://www.tiktok.com" + href, wait_until="commit", timeout=25000)
                        page.wait_for_timeout(3000)
                body = ""
                try:
                    body = page.locator("body").inner_text()[:4000]
                except Exception:
                    pass
                results[name] = {
                    "url": page.url,
                    "title": page.title(),
                    "body": body,
                }
            except Exception as exc:
                results[name] = {
                    "url": page.url,
                    "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                }
            finally:
                page.close()
        browser.close()
    payload = {"collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "platforms": results}
    out = root / "data" / "account_inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
