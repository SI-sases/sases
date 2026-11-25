#!/usr/bin/env python3
"""Minimal browser executor for local SASES.

Runs a Chromium page through Playwright and returns title/URL.
Used as the base for platform publishing adapters.
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
    parser.add_argument("url")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--profile", default="")
    args = parser.parse_args()

    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or DEFAULT_CHROME
    if not os.path.isfile(executable):
        print(json.dumps({"ok": False, "error": "chromium not found", "path": executable}, ensure_ascii=False))
        return 2

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = None
        if args.profile:
            context = p.chromium.launch_persistent_context(
                args.profile,
                headless=not args.headed,
                executable_path=executable,
                args=["--disable-blink-features=AutomationControlled"],
                locale="zh-CN",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = p.chromium.launch(
                headless=not args.headed,
                executable_path=executable,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                locale="zh-CN",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

        def close() -> None:
            try:
                context.close()
            finally:
                if browser is not None:
                    browser.close()

        try:
            response = page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout)
            page.wait_for_timeout(1500)
        except Exception as exc:
            if args.screenshot:
                os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
                try:
                    page.screenshot(path=args.screenshot, full_page=False)
                except Exception:
                    pass
            print(json.dumps({
                "ok": False,
                "url": page.url,
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                "screenshot": args.screenshot or None,
                "profile": args.profile or None,
            }, ensure_ascii=False))
            close()
            return 1
        if args.screenshot:
            os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
            page.screenshot(path=args.screenshot, full_page=True)
        result = {
            "ok": True,
            "url": page.url,
            "title": page.title(),
            "status": response.status if response else None,
            "screenshot": args.screenshot or None,
            "profile": args.profile or None,
        }
        print(json.dumps(result, ensure_ascii=False))
        close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
