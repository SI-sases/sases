#!/usr/bin/env python3
"""Open or close one isolated browser tab for a local task."""
from __future__ import annotations

import argparse
import json
import os

DEFAULT_CDP = os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["new", "close"])
    parser.add_argument("--cdp", default=DEFAULT_CDP)
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        try:
            name = args.name.strip()
            if args.action == "new":
                page = context.new_page()
                if name:
                    page.evaluate("(name) => { window.name = name; }", name)
                result = {"ok": True, "action": "new", "pages": len(context.pages),
                          "name": name, "url": page.url}
            else:
                closed = False
                target = None
                if name:
                    for candidate in context.pages:
                        try:
                            if candidate.evaluate("() => window.name") == name:
                                target = candidate
                                break
                        except Exception:
                            continue
                if target is not None and len(context.pages) > 1:
                    target.close()
                    closed = True
                elif len(context.pages) > 1:
                    context.pages[-1].close()
                    closed = True
                result = {"ok": True, "action": "close", "closed": closed,
                          "name": name, "pages": len(context.pages)}
            print(json.dumps(result, ensure_ascii=False))
            browser.close()
            return 0
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "action": args.action,
                              "error": f"{type(exc).__name__}: {str(exc)[:200]}"}, ensure_ascii=False))
            try:
                browser.close()
            except Exception:
                pass
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
