"""Bounded recovery suggestions for a failed browser task.

The default mode is observe-only: it never clicks or submits. It turns a page
snapshot into a short list of safe next actions for the main AGI.
"""
from __future__ import annotations

import os


def plan(snapshot: dict, goal: str = "") -> dict:
    state = str(snapshot.get("state") or "unknown")
    if state == "upload_limit":
        return {"mode": "observe", "state": state,
                "summary": "平台上传额度已耗尽，等待恢复或切换平台。",
                "actions": [], "automatic": False}
    if state == "login_required":
        return {"mode": "observe", "state": state,
                "summary": "平台登录态失效，需要人工登录。",
                "actions": [], "automatic": False}
    if state == "captcha_or_challenge":
        return {"mode": "observe", "state": state,
                "summary": "页面出现验证，需要人工处理。",
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
        "summary": f"页面可继续操作；找到 {len(buttons)} 个按钮、{len(inputs)} 个输入框。",
        "actions": (buttons + inputs)[:8],
        "automatic": False,
    }
