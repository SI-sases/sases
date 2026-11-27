#!/usr/bin/env python3
"""Small Playwright action worker for the AGI browser tools.

It connects to the existing CDP browser by default.  It never stores
credentials; the browser profile owns the login session.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_CHROME = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "ms-playwright",
    "chromium-1243",
    "chrome-win64",
    "chrome.exe",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="")
    parser.add_argument("--cdp", default=os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222"))
    parser.add_argument("--fill", action="append", default=[], metavar="SELECTOR=VALUE")
    parser.add_argument("--click", default="")
    parser.add_argument("--wait-ms", type=int, default=1500)
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--screenshot", default="")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        result = {"ok": True, "actions": [], "url": page.url}
        try:
            if args.url:
                page.goto(args.url, wait_until="commit", timeout=args.timeout)
                page.wait_for_timeout(args.wait_ms)
                result["url"] = page.url
                result["title"] = page.title()
            for item in args.fill:
                if "=" not in item:
                    raise ValueError("--fill must be SELECTOR=VALUE")
                selector, value = item.split("=", 1)
                page.locator(selector).fill(value)
                result["actions"].append({"fill": selector})
            if args.click:
                page.locator(args.click).click()
                page.wait_for_timeout(args.wait_ms)
                result["actions"].append({"click": args.click})
            if args.screenshot:
                os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
                page.screenshot(path=args.screenshot, full_page=True)
                result["screenshot"] = args.screenshot
            result["url"] = page.url
            result["title"] = page.title()
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                      "url": page.url, "actions": result.get("actions", [])}
            if args.screenshot:
                try:
                    page.screenshot(path=args.screenshot, full_page=False)
                    result["screenshot"] = args.screenshot
                except Exception:
                    pass
            print(json.dumps(result, ensure_ascii=False))
            browser.close()
            return 1
        print(json.dumps(result, ensure_ascii=False))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
