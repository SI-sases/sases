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
    parser.add_argument("--click-target", default="", help="JSON target: selector/role/name/text/label/placeholder")
    parser.add_argument("--fill-target", action="append", default=[], help="JSON {target,value}")
    parser.add_argument("--wait-target", default="", help="JSON target to wait for")
    parser.add_argument("--extract-target", default="", help="JSON target to extract")
    parser.add_argument("--upload-target", default="", help="JSON {target,path}")
    parser.add_argument("--wait-ms", type=int, default=1500)
    parser.add_argument("--timeout", type=int, default=30000)
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--no-reuse", action="store_true", help="always navigate")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        result = {"ok": True, "actions": [], "url": page.url}
        def resolve(target, require_visible=True):
            if isinstance(target, str):
                target = {"selector": target}
            timeout = args.timeout
            attempts = []
            if target.get("selector"):
                attempts.append(("selector", lambda: page.locator(target["selector"])))
            if target.get("role"):
                attempts.append(("role", lambda: page.get_by_role(target["role"], name=target.get("name") or None)))
            if target.get("label"):
                attempts.append(("label", lambda: page.get_by_label(target["label"])))
            if target.get("placeholder"):
                attempts.append(("placeholder", lambda: page.get_by_placeholder(target["placeholder"])))
            if target.get("text"):
                attempts.append(("text", lambda: page.get_by_text(target["text"], exact=bool(target.get("exact")))))
            errors = []
            for kind, make in attempts:
                try:
                    loc = make().first
                    if require_visible:
                        loc.wait_for(state="visible", timeout=timeout)
                    else:
                        loc.wait_for(state="attached", timeout=timeout)
                    return loc, kind
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{kind}: {type(exc).__name__}")
            raise TimeoutError("; ".join(errors) or "empty target")

        try:
            if args.url:
                target = args.url.rstrip("/")
                current = page.url.rstrip("/")
                if not args.no_reuse and current.split("?")[0] == target.split("?")[0]:
                    result["reused"] = True
                else:
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
            for item in args.fill_target:
                spec = json.loads(item)
                loc, kind = resolve(spec.get("target") or {})
                loc.fill(str(spec.get("value") or ""))
                result["actions"].append({"fill": spec.get("target"), "resolved_by": kind})
            if args.click:
                page.locator(args.click).click()
                page.wait_for_timeout(args.wait_ms)
                result["actions"].append({"click": args.click})
            if args.click_target:
                loc, kind = resolve(json.loads(args.click_target))
                loc.click()
                page.wait_for_timeout(args.wait_ms)
                result["actions"].append({"click": json.loads(args.click_target), "resolved_by": kind})
            if args.wait_target:
                loc, kind = resolve(json.loads(args.wait_target))
                result["waited"] = {"target": json.loads(args.wait_target), "resolved_by": kind}
            if args.extract_target:
                target = json.loads(args.extract_target)
                loc, kind = resolve(target)
                try:
                    value = loc.input_value(timeout=5000)
                except Exception:
                    value = loc.inner_text(timeout=5000)
                result["extracted"] = {"target": target, "resolved_by": kind, "value": value}
            if args.upload_target:
                spec = json.loads(args.upload_target)
                loc, kind = resolve(spec.get("target") or {}, require_visible=False)
                loc.set_input_files(str(spec.get("path") or ""))
                result["actions"].append({"upload": spec, "resolved_by": kind})
            if args.screenshot:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
                    page.screenshot(path=args.screenshot, full_page=False, timeout=10000)
                    result["screenshot"] = args.screenshot
                except Exception as exc:  # noqa: BLE001
                    result["screenshot_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
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
