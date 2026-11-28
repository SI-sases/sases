"""Bounded recovery suggestions for a failed browser task.

The default mode is observe-only: it never clicks or submits. It turns a page
snapshot into a short list of safe next actions for the main AGI.
"""
from __future__ import annotations

import os


def plan(snapshot: dict, goal: str = "", profile: str = "default",
         profiles: list[str] | None = None) -> dict:
    state = str(snapshot.get("state") or "unknown")
    if state == "upload_limit":
        return {"mode": "observe", "state": state,
                "summary": "platform upload limit reached; wait or switch platform",
                "fallback": {"type": "switch_platform", "platforms": ["bilibili", "douyin"]},
                "actions": [], "automatic": False}
    if state == "login_required":
        alternatives = [p for p in (profiles or []) if p != profile]
        return {"mode": "observe", "state": state,
                "summary": "login required; manual login or another profile",
                "fallback": {"type": "switch_profile", "profiles": alternatives},
                "actions": [], "automatic": False}
    if state == "captcha_or_challenge":
        return {"mode": "observe", "state": state,
                "summary": "captcha or challenge requires a human",
                "actions": [], "automatic": False}

    elements = snapshot.get("elements") or []
    buttons = []
    inputs = []
    for el in elements:
        if not el.get("visible", True):
            continue
        text = str(el.get("text") or "").strip()
        placeholder = str(el.get("placeholder") or "").strip()
        name = str(el.get("name") or "").strip()
        if el.get("tag") == "button" or el.get("role") == "button":
            target = {"text": text} if text else ({"name": name} if name else {})
            if target:
                buttons.append({"tool": "browser.click_target", "target": target})
        elif el.get("tag") in ("input", "textarea") and el.get("type") not in ("file", "checkbox", "radio"):
            target = {"placeholder": placeholder} if placeholder else ({"name": name} if name else {})
            if target:
                inputs.append({"tool": "browser.fill_targets", "target": target})
    return {
        "mode": os.environ.get("SASES_BROWSER_AGENT", "observe"),
        "state": state,
        "summary": f"page can continue; {len(buttons)} buttons, {len(inputs)} inputs",
        "actions": (buttons + inputs)[:8],
        "automatic": False,
    }
