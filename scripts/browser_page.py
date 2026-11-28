"""Select the browser tab owned by the current local task."""
from __future__ import annotations

import os


def page_name() -> str:
    return os.environ.get("SASES_BROWSER_PAGE_NAME", "").strip()


def select(context):
    name = page_name()
    if name:
        for page in context.pages:
            try:
                if page.evaluate("() => window.name") == name:
                    return page
            except Exception:
                continue
    return context.pages[-1] if context.pages else context.new_page()
