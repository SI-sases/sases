#!/usr/bin/env python3
"""Read-only page snapshot for the local CDP browser."""
from __future__ import annotations

import argparse
import json
import os
import time

DEFAULT_CDP = os.environ.get("SASES_CDP_URL", "http://127.0.0.1:9222")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp", default=DEFAULT_CDP)
    parser.add_argument("--screenshot", default="")
    parser.add_argument("--max-elements", type=int, default=200)
    parser.add_argument("--timeout", type=int, default=15000)
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[-1] if context.pages else context.new_page()
        try:
            page.wait_for_timeout(300)
            try:
                info = page.evaluate(
                    """
                (limit) => {
                  const q = 'button,a,input,textarea,select,[role=button],[role=textbox],[contenteditable=true]';
                  const visible = (el) => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
                  };
                  const rows = [];
                  for (const el of Array.from(document.querySelectorAll(q)).slice(0, limit)) {
                    rows.push({
                      tag: el.tagName.toLowerCase(),
                      role: el.getAttribute('role') || '',
                      type: el.getAttribute('type') || '',
                      name: el.getAttribute('aria-label') || el.getAttribute('name') || '',
                      text: (el.innerText || el.value || '').trim().slice(0, 160),
                      placeholder: el.getAttribute('placeholder') || '',
                      visible: visible(el),
                      disabled: !!el.disabled,
                    });
                  }
                  return {
                    url: location.href,
                    title: document.title,
                    text: (document.body ? document.body.innerText : '').slice(-4000),
                    elements: rows,
                    dialogs: Array.from(document.querySelectorAll('[role=dialog], tp-yt-paper-dialog, .modal')).slice(0, 20).map((d) => ({
                      text: (d.innerText || '').trim().slice(0, 800),
                      visible: visible(d),
                    })),
                  };
                }
                """,
                    max(1, min(args.max_elements, 500)),
                )
            except Exception as exc:  # noqa: BLE001
                info = {"url": page.url, "title": page.title(), "text": "", "elements": [],
                        "dialogs": [], "snapshot_error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            result = {"ok": True, **info, "captured_at": int(time.time())}
            if args.screenshot:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
                    page.screenshot(path=args.screenshot, full_page=False, timeout=min(args.timeout, 10000))
                    result["screenshot"] = args.screenshot
                except Exception as exc:  # noqa: BLE001
                    result["screenshot_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            print(json.dumps(result, ensure_ascii=False))
            browser.close()
            return 0
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"},
                             ensure_ascii=False))
            try:
                browser.close()
            except Exception:
                pass
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
