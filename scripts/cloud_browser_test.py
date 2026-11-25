#!/usr/bin/env python3
"""Smoke test for the cloud browser container."""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

TARGETS = [
    "https://example.com",
    "https://www.xiaohongshu.com/",
]


def main() -> int:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        for url in TARGETS:
            try:
                response = page.goto(url, wait_until="commit", timeout=25000)
                page.wait_for_timeout(2000)
                results.append({
                    "url": url,
                    "final_url": page.url,
                    "title": page.title(),
                    "status": response.status if response else None,
                })
            except Exception as exc:
                results.append({"url": url, "error": f"{type(exc).__name__}: {str(exc)[:160]}"})
        browser.close()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
