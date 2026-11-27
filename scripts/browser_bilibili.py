#!/usr/bin/env python3
"""Bilibili video upload worker used by the AGI adapter."""
from __future__ import annotations

import argparse
import json
import os

URL = "https://member.bilibili.com/platform/upload/video/frame"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--tags", default="AI,自托管,开源")
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
        result = {"ok": True, "dry_run": args.dry_run, "platform": "bilibili"}
        try:
            page.goto(URL, wait_until="commit", timeout=args.timeout)
            page.wait_for_timeout(5000)
            with page.expect_file_chooser(timeout=10000) as chooser:
                page.locator(".upload-area").click()
            chooser.value.set_files(args.video)
            page.wait_for_timeout(15000)
            # A cover is required by the publish form.
            page.get_by_text("添加封面", exact=True).click()
            page.wait_for_timeout(1500)
            page.get_by_text("完成", exact=True).last.click()
            page.wait_for_timeout(1500)
            page.locator('input[placeholder="请输入稿件标题"]').fill(args.title)
            tag_input = page.locator('input[placeholder="按回车键Enter创建标签"]').first
            for tag in [t.strip() for t in args.tags.split(",") if t.strip()]:
                tag_input.fill(tag)
                tag_input.press("Enter")
                page.wait_for_timeout(250)
            if args.description:
                page.locator("[contenteditable=true]").first.fill(args.description)
            page.locator('input[placeholder="请选择符合您视频内容的创作声明"]').click()
            page.wait_for_timeout(400)
            page.get_by_text("含AI生成内容", exact=True).last.click()
            page.wait_for_timeout(600)
            if args.dry_run:
                result["url"] = page.url
                result["published"] = False
            else:
                page.get_by_text("立即投稿", exact=True).click()
                page.wait_for_timeout(15000)
                body = page.locator("body").inner_text()
                result["submitted"] = "稿件投递成功" in body
                result["url"] = page.url
                if not result["submitted"]:
                    result["ok"] = False
                    result["error"] = "publish confirmation not found"
            if args.screenshot:
                try:
                    page.screenshot(path=args.screenshot, full_page=False, timeout=10000)
                    result["screenshot"] = args.screenshot
                except Exception as exc:
                    result["screenshot_error"] = type(exc).__name__
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
