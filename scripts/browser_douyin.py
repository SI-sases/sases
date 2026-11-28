#!/usr/bin/env python3
"""Douyin image-post worker used by the AGI adapter."""
from __future__ import annotations

import argparse
import json
import os
from browser_checkpoint import load as load_checkpoint, save as save_phase, clear as clear_checkpoint
import sys

DEFAULT_CHROME = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "ms-playwright",
    "chromium-1243",
    "chrome-win64",
    "chrome.exe",
)


from browser_page import select as select_page


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--cdp", default=os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--timeout", type=int, default=30000)
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = select_page(context)
        result = {"ok": True, "dry_run": args.dry_run, "platform": "douyin"}
        try:
            phase = load_checkpoint().get("phase", "")
            resumed = (phase in ("uploaded", "filled")
                       and page.url.startswith("https://creator.douyin.com/creator-micro/content/post/image")
                       and page.locator("[contenteditable=true]").count() > 0)
            if resumed:
                result["resumed"] = phase
            else:
                phase = ""
                page.goto("https://creator.douyin.com/creator-micro/content/upload",
                          wait_until="commit", timeout=args.timeout)
                page.wait_for_timeout(5000)
                page.get_by_text("发布图文", exact=True).click()
                page.wait_for_timeout(2000)
                page.locator("input[type=file]").last.set_input_files(args.image)
                page.wait_for_timeout(15000)
                save_phase("uploaded")
            if phase not in ("filled",):
                editor = page.locator("[contenteditable=true]").first
                editor.click()
                editor.fill(args.description)
                page.wait_for_timeout(1000)
                save_phase("filled")
            if not args.dry_run:
                page.get_by_role("button", name="发布", exact=True).click()
                page.wait_for_timeout(12000)
                body = page.locator("body").inner_text()
                result["url"] = page.url
                result["published"] = "已发布" in body and args.description[:12] in body
                if result["published"]:
                    save_phase("published")
                if not result["published"]:
                    result["ok"] = False
                    result["error"] = "publish confirmation not found"
            else:
                result["url"] = page.url
                result["published"] = False
            if args.screenshot:
                try:
                    page.screenshot(path=args.screenshot, full_page=False, timeout=10000)
                    result["screenshot"] = args.screenshot
                except Exception as exc:
                    result["screenshot_error"] = type(exc).__name__
            if result.get("ok"):
                clear_checkpoint()
            print(json.dumps(result, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "dry_run": args.dry_run,
                              "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                              "url": page.url}, ensure_ascii=False))
            browser.close()
            return 1
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
