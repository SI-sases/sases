#!/usr/bin/env python3
"""Reddit submit worker used by the AGI Reddit playbook."""
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
    parser.add_argument("--subreddit", default="selfhostedstack")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--cdp", default=os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--no-reuse", action="store_true", help="always navigate")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        result = {"ok": True, "dry_run": args.dry_run, "subreddit": args.subreddit}
        try:
            target = f"https://www.reddit.com/r/{args.subreddit}/submit"
            if not args.no_reuse and page.url.rstrip("/").startswith(target.rstrip("/")):
                result["reused"] = True
            else:
                page.goto(target, wait_until="commit", timeout=args.timeout)
                page.wait_for_timeout(6000)
            page.locator("textarea[placeholder='标题']").fill(args.title)
            body = page.locator("[contenteditable=true]").last
            body.click()
            body.fill(args.body)
            page.wait_for_timeout(800)
            if not args.dry_run:
                page.get_by_text("发帖", exact=True).last.click()
                page.wait_for_timeout(6000)
                result["submitted"] = True
                result["url"] = page.url
            else:
                result["submitted"] = False
                result["url"] = page.url
            if args.screenshot:
                os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
                page.screenshot(path=args.screenshot, full_page=True)
                result["screenshot"] = args.screenshot
            result["title"] = page.title()
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "dry_run": args.dry_run,
                      "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                      "url": page.url}
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
