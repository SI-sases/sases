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

    ckpt_path = os.environ.get("SASES_CHECKPOINT_FILE", "")
    ckpt = {}
    if ckpt_path and os.path.isfile(ckpt_path):
        try:
            ckpt = json.loads(open(ckpt_path, encoding="utf-8").read() or "{}")
        except Exception:
            ckpt = {}

    def save_phase(phase: str) -> None:
        if not ckpt_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(ckpt_path)), exist_ok=True)
            open(ckpt_path, "w", encoding="utf-8").write(json.dumps({"phase": phase}))
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        result = {"ok": True, "dry_run": args.dry_run, "subreddit": args.subreddit}
        try:
            target = f"https://www.reddit.com/r/{args.subreddit}/submit"
            on_target = page.url.rstrip("/").startswith(target.rstrip("/"))
            if not args.no_reuse and on_target:
                result["reused"] = True
            else:
                page.goto(target, wait_until="commit", timeout=args.timeout)
                page.wait_for_timeout(6000)
            phase = ckpt.get("phase", "")
            page_ready = (page.locator("textarea").count() > 0
                          and page.locator("[contenteditable=true]").count() > 0)
            if phase in ("filled", "submitted") and on_target and page_ready:
                result["resumed"] = phase
            else:
                page.locator("textarea").first.fill(args.title)
                body = page.locator("[contenteditable=true]").last
                body.click()
                body.fill(args.body)
                page.wait_for_timeout(800)
                save_phase("filled")
            if not args.dry_run:
                page.get_by_text("发帖", exact=True).last.click()
                page.wait_for_timeout(6000)
                result["submitted"] = True
                result["url"] = page.url
                save_phase("submitted")
                if "/comments/" not in page.url:
                    result["ok"] = False
                    result["error"] = "submit did not reach a post URL"
            else:
                result["submitted"] = False
                result["url"] = page.url
            if args.screenshot:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
                    page.screenshot(path=args.screenshot, full_page=True)
                    result["screenshot"] = args.screenshot
                except Exception as exc:
                    result["screenshot_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            result["title"] = page.title()
        except Exception as exc:  # noqa: BLE001
            submitted = "/comments/" in page.url
            result = {"ok": submitted, "dry_run": args.dry_run,
                      "submitted": submitted, "url": page.url,
                      "error": None if submitted else f"{type(exc).__name__}: {str(exc)[:300]}"}
            if args.screenshot:
                try:
                    page.screenshot(path=args.screenshot, full_page=False)
                    result["screenshot"] = args.screenshot
                except Exception:
                    pass
            print(json.dumps(result, ensure_ascii=False))
            browser.close()
            return 0 if submitted else 1
        if result.get("ok") and ckpt_path:
            try:
                os.remove(ckpt_path)
            except Exception:
                pass
        print(json.dumps(result, ensure_ascii=False))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
