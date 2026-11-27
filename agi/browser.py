"""Browser tools backed by the local CDP Playwright worker."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _python() -> str:
    explicit = os.environ.get("SASES_BROWSER_PYTHON", "").strip()
    if explicit and Path(explicit).exists():
        return explicit
    return sys.executable


def _run_cmd(cmd: list[str], timeout: int = 90) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=str(_root()), encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "browser action timed out"}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1] or "{}")
    except Exception:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "browser worker failed")[-800:]}


def _run(args: list[str], timeout: int = 90) -> dict[str, Any]:
    script = _root() / "scripts" / "browser_act.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_act.py missing"}
    return _run_cmd([_python(), str(script), *args], timeout)


from .platform_policy import check as policy_check


def _policy(url: str, action: str, approved: bool) -> dict | None:
    decision = policy_check(url, action, approved)
    if decision.get("allowed"):
        return None
    return {"ok": False, "error": "platform_manual_only", **decision}


def open_page(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "")
    if not url:
        return {"ok": False, "error": "url is required"}
    denied = _policy(url, "open_for_human", bool(args.get("manual_approved")))
    if denied:
        return denied
    cmd = ["--url", url, "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def fill_page(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "")
    fields = args.get("fields") or {}
    if not isinstance(fields, dict) or not fields:
        return {"ok": False, "error": "fields must be a non-empty object"}
    if url:
        denied = _policy(url, "fill", bool(args.get("manual_approved")))
        if denied:
            return denied
    cmd = ["--url", url, "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    for selector, value in fields.items():
        cmd += ["--fill", f"{selector}={value}"]
    if args.get("click"):
        cmd += ["--click", str(args["click"])]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def click_page(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "")
    selector = str(args.get("selector") or "")
    if not selector:
        return {"ok": False, "error": "selector is required"}
    if url:
        denied = _policy(url, "click", bool(args.get("manual_approved")))
        if denied:
            return denied
    cmd = ["--url", url, "--click", selector, "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def reddit_post(args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title") or "")
    body = str(args.get("body") or "")
    dry_run = bool(args.get("dry_run", True))
    if not title or not body:
        return {"ok": False, "error": "title and body are required"}
    if not dry_run and not args.get("approved"):
        return {"ok": False, "error": "approval_required", "requires_approval": True,
                "tool": "browser.reddit_post", "title": title}
    script = _root() / "scripts" / "browser_reddit.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_reddit.py missing"}
    cmd = [
        _python(), str(script),
        "--subreddit", str(args.get("subreddit") or "selfhostedstack"),
        "--title", title,
        "--body", body,
    ]
    if dry_run:
        cmd.append("--dry-run")
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run_cmd(cmd, timeout=120)


def douyin_post(args: dict[str, Any]) -> dict[str, Any]:
    image = str(args.get("image") or "")
    description = str(args.get("description") or "")
    dry_run = bool(args.get("dry_run", True))
    if not image or not os.path.isfile(image):
        return {"ok": False, "error": "image file is required"}
    if not description:
        return {"ok": False, "error": "description is required"}
    if not dry_run and not args.get("approved"):
        return {"ok": False, "error": "approval_required", "requires_approval": True,
                "tool": "browser.douyin_post"}
    script = _root() / "scripts" / "browser_douyin.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_douyin.py missing"}
    cmd = [_python(), str(script), "--image", image, "--description", description]
    if dry_run:
        cmd.append("--dry-run")
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run_cmd(cmd, timeout=120)


def bilibili_post(args: dict[str, Any]) -> dict[str, Any]:
    video = str(args.get("video") or "")
    title = str(args.get("title") or "")
    dry_run = bool(args.get("dry_run", True))
    if not video or not os.path.isfile(video):
        return {"ok": False, "error": "video file is required"}
    if not title:
        return {"ok": False, "error": "title is required"}
    if not dry_run and not args.get("approved"):
        return {"ok": False, "error": "approval_required", "requires_approval": True,
                "tool": "browser.bilibili_post"}
    script = _root() / "scripts" / "browser_bilibili.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_bilibili.py missing"}
    cmd = [_python(), str(script), "--video", video, "--title", title,
           "--description", str(args.get("description") or ""),
           "--tags", str(args.get("tags") or "AI,自托管,开源")]
    if dry_run:
        cmd.append("--dry-run")
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run_cmd(cmd, timeout=180)
