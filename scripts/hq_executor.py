#!/usr/bin/env python3
"""Local HQ executor: claim approved tasks and publish through Edge CDP."""
from __future__ import annotations

import argparse
import json
import os
import time

import httpx

HQ = os.environ.get("SASES_HQ_URL", "http://127.0.0.1:8001").rstrip("/")
TOKEN = os.environ.get("SASES_LINK_TOKEN", "")
CDP = os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222")


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    jwt_token = os.environ.get("SASES_HQ_TOKEN", "")
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"
    else:
        headers["X-SASES-Link-Token"] = TOKEN
    return headers


def _publish_x(text: str, image: str = "") -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        try:
            page.goto("https://x.com/compose/post", wait_until="commit", timeout=25000)
            page.wait_for_timeout(4000)
            page.locator('[data-testid="tweetTextarea_0"]').first.fill(text)
            page.wait_for_timeout(800)
            page.locator('[data-testid="tweetButton"]').first.click()
            page.wait_for_timeout(5000)
            return {"ok": True, "platform": "x", "url": page.url, "text": text[:200]}
        finally:
            page.close()
            browser.close()


def publish(task: dict, dry_run: bool = False) -> dict:
    platform = (task.get("platform") or "").lower()
    payload = task.get("payload") or {}
    content = payload.get("content") if isinstance(payload.get("content"), dict) else payload
    text = content.get("body") or content.get("text") or payload.get("text") or ""
    if dry_run:
        return {"ok": True, "dry_run": True, "platform": platform, "text": text[:200]}
    if platform == "x":
        return _publish_x(text)
    return {
        "ok": False,
        "platform": platform,
        "error": "adapter_not_implemented",
        "hint": "当前正式适配器只有 X；小红书/抖音/TikTok 需继续接入",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--platform", default=None)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    while True:
        with httpx.Client(base_url=HQ, timeout=20, trust_env=False) as c:
            r = c.post("/hq/tasks/claim", params={"platform": args.platform} if args.platform else None, headers=_headers())
            if r.status_code != 200:
                print("claim error", r.status_code, r.text[:200])
                task = None
            else:
                task = r.json().get("task")
            if not task:
                if args.once:
                    return 0
                time.sleep(args.interval)
                continue
            print("task", task["id"], task["platform"])
            try:
                result = publish(task, args.dry_run)
                status = "done" if result.get("ok") else "failed"
            except Exception as exc:
                result = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
                status = "failed"
            receipt = c.post(
                f"/hq/tasks/{task['id']}/receipt",
                headers=_headers(),
                json={"status": status, "result": result, "error": None if status == "done" else result.get("error")},
            )
            print("receipt", receipt.status_code, receipt.text[:300])
            if args.once:
                return 0


if __name__ == "__main__":
    raise SystemExit(main())
