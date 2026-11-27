#!/usr/bin/env python3
"""YouTube Studio upload worker used by the AGI adapter."""
from __future__ import annotations

import argparse
import json
import os
from browser_checkpoint import save as save_phase, clear as clear_checkpoint

UPLOAD = "https://studio.youtube.com/channel/UCBpL3hK22rzoNP70J8evpHQ/videos/upload"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--cdp", default=os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--timeout", type=int, default=30000)
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        result = {"ok": True, "dry_run": args.dry_run, "platform": "youtube"}
        try:
            page.goto(UPLOAD, wait_until="commit", timeout=args.timeout)
            page.wait_for_timeout(6000)
            page.get_by_role("button", name="上传视频").click()
            page.wait_for_timeout(1200)
            page.locator("input[type=file]").set_input_files(args.video)
            page.wait_for_timeout(10000)
            save_phase("uploaded")
            editors = page.locator("[contenteditable=true]")
            editors.nth(0).click()
            editors.nth(0).fill(args.title)
            editors.nth(1).click()
            editors.nth(1).fill(args.description)
            page.get_by_text("不，内容不是面向儿童的", exact=False).click()
            page.wait_for_timeout(400)
            save_phase("details")
            for _ in range(3):
                page.get_by_role("button", name="继续").click()
                page.wait_for_timeout(1800)
            save_phase("visibility")
            if args.dry_run:
                result["url"] = page.url
                result["published"] = False
            else:
                page.locator('tp-yt-paper-radio-button[name="PUBLIC"]').click()
                page.wait_for_timeout(800)
                page.get_by_role("button", name="发布").click()
                page.wait_for_timeout(12000)
                body = page.locator("body").inner_text()
                result["url"] = page.url
                result["published"] = "已发布" in body or "视频已发布" in body
                if result["published"]:
                    save_phase("published")
                if not result["published"]:
                    result["ok"] = False
                    result["error"] = "publish confirmation not found"
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
