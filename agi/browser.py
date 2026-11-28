"""Browser tools backed by the local CDP Playwright worker."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


_cdp_local = threading.local()


def set_cdp(url: str = "") -> None:
    _cdp_local.url = url or ""


def get_cdp() -> str:
    return getattr(_cdp_local, "url", "") or ""


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _python() -> str:
    explicit = os.environ.get("SASES_BROWSER_PYTHON", "").strip()
    if explicit and Path(explicit).exists():
        return explicit
    return sys.executable


def _run_cmd(cmd: list[str], timeout: int = 90) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if get_cdp():
        env["SASES_CDP_URL"] = get_cdp()
    agent_id = env.get("SASES_AGENT_ID", "").strip()
    if agent_id:
        ckpt_dir = _root() / "data" / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        env["SASES_CHECKPOINT_FILE"] = str(ckpt_dir / f"{agent_id}.json")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=str(_root()), encoding="utf-8", errors="replace", env=env)
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
from .content_policy import sanitize as sanitize_content


def _policy(url: str, action: str, approved: bool) -> dict | None:
    decision = policy_check(url, action, approved)
    if decision.get("allowed"):
        return None
    return {"ok": False, "error": "platform_manual_only", **decision}


def snapshot(args: dict[str, Any]) -> dict[str, Any]:
    from .browser_snapshot import capture
    return capture(str(args.get("screenshot") or ""),
                   int(args.get("max_elements") or 200),
                   int(args.get("timeout") or 30))


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


def click_target(args: dict[str, Any]) -> dict[str, Any]:
    target = args.get("target") or {}
    if not isinstance(target, dict) or not any(target.values()):
        return {"ok": False, "error": "target must include selector/role/name/text/label/placeholder"}
    if args.get("url"):
        denied = _policy(str(args["url"]), "click", bool(args.get("manual_approved")))
        if denied:
            return denied
    cmd = ["--click-target", json.dumps(target, ensure_ascii=False),
           "--wait-ms", str(int(args.get("wait_ms") or 1500))]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def fill_targets(args: dict[str, Any]) -> dict[str, Any]:
    targets = args.get("targets") or []
    if not isinstance(targets, list) or not targets:
        return {"ok": False, "error": "targets must be a non-empty list"}
    cmd = ["--wait-ms", str(int(args.get("wait_ms") or 1500))]
    for item in targets:
        cmd += ["--fill-target", json.dumps(item, ensure_ascii=False)]
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run(cmd)


def wait_for(args: dict[str, Any]) -> dict[str, Any]:
    target = args.get("target") or {}
    if not isinstance(target, dict) or not any(target.values()):
        return {"ok": False, "error": "target must include selector/role/name/text/label/placeholder"}
    return _run(["--wait-target", json.dumps(target, ensure_ascii=False)])


def extract(args: dict[str, Any]) -> dict[str, Any]:
    target = args.get("target") or {}
    if not isinstance(target, dict) or not any(target.values()):
        return {"ok": False, "error": "target must include selector/role/name/text/label/placeholder"}
    return _run(["--extract-target", json.dumps(target, ensure_ascii=False)])


def upload(args: dict[str, Any]) -> dict[str, Any]:
    target = args.get("target") or {}
    path = str(args.get("path") or "")
    if not isinstance(target, dict) or not any(target.values()) or not path:
        return {"ok": False, "error": "target and path are required"}
    if not Path(path).exists():
        return {"ok": False, "error": f"upload file not found: {path}"}
    return _run(["--upload-target", json.dumps({"target": target, "path": path}, ensure_ascii=False)])


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
    title = sanitize_content(str(args.get("title") or ""))
    body = sanitize_content(str(args.get("body") or ""))
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
    description = sanitize_content(str(args.get("description") or ""))
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
    title = sanitize_content(str(args.get("title") or ""))
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
           "--description", sanitize_content(str(args.get("description") or "")),
           "--tags", str(args.get("tags") or "AI,自托管,开源")]
    if dry_run:
        cmd.append("--dry-run")
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run_cmd(cmd, timeout=180)


def youtube_post(args: dict[str, Any]) -> dict[str, Any]:
    video = str(args.get("video") or "")
    title = sanitize_content(str(args.get("title") or ""))
    dry_run = bool(args.get("dry_run", True))
    if not video or not os.path.isfile(video):
        return {"ok": False, "error": "video file is required"}
    if not title:
        return {"ok": False, "error": "title is required"}
    if not dry_run and not args.get("approved"):
        return {"ok": False, "error": "approval_required", "requires_approval": True,
                "tool": "browser.youtube_post"}
    script = _root() / "scripts" / "browser_youtube.py"
    if not script.exists():
        return {"ok": False, "error": "scripts/browser_youtube.py missing"}
    cmd = [_python(), str(script), "--video", video, "--title", title,
           "--description", sanitize_content(str(args.get("description") or ""))]
    if dry_run:
        cmd.append("--dry-run")
    if args.get("screenshot"):
        cmd += ["--screenshot", str(args["screenshot"])]
    return _run_cmd(cmd, timeout=180)
