"""Platform automation policy.

Xiaohongshu is currently manual-only after a platform risk warning.  The
policy is enforced in the browser tools, not just documented.
"""
from __future__ import annotations

from urllib.parse import urlparse

POLICIES = {
    "xiaohongshu": {
        "mode": "manual",
        "risk": "warning",
        "reason": "platform warned about non-human browsing",
        "allowed": ["open_for_human", "screenshot"],
    },
    "reddit": {"mode": "approval", "risk": "normal", "allowed": ["open", "fill", "click", "submit"]},
    "douyin": {"mode": "approval", "risk": "normal", "allowed": ["open", "fill", "click"]},
    "bilibili": {"mode": "approval", "risk": "normal", "allowed": ["open", "fill", "click"]},
    "youtube": {"mode": "approval", "risk": "normal", "allowed": ["open", "fill", "click"]},
}


def platform_for(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if "xiaohongshu" in host or host in {"xhslink.com", "xhs.cn"}:
        return "xiaohongshu"
    if "reddit" in host:
        return "reddit"
    if "douyin" in host:
        return "douyin"
    if "bilibili" in host:
        return "bilibili"
    if "youtube" in host:
        return "youtube"
    return ""


def check(url: str, action: str, manual_approved: bool = False) -> dict:
    platform = platform_for(url)
    if not platform:
        return {"allowed": True, "platform": "", "mode": "open"}
    policy = POLICIES[platform]
    if policy["mode"] == "manual":
        return {
            "allowed": bool(manual_approved and action == "open_for_human"),
            "platform": platform,
            "mode": "manual",
            "reason": policy["reason"],
        }
    return {"allowed": True, "platform": platform, "mode": policy["mode"]}
