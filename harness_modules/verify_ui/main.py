# harness_modules/verify_ui/main.py
# -*- coding: utf-8 -*-
"""轻量 UI 验证：Chrome headless CLI，不依赖 Playwright。

支持：
  screenshot     截图到 static/_ui_shots/
  check_element  检查简单 selector（#id / .class / tag）
  check_text     DOM 中包含指定文本
仅允许 http://127.0.0.1:8001/ 与 http://localhost:8001/
"""
import os
import re
import shutil
import subprocess
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHOT_DIR = os.path.join(REPO_ROOT, "static", "_ui_shots")
ALLOWED = ("http://127.0.0.1:8001/", "http://localhost:8001/")

CHROME_CANDIDATES = [
    os.getenv("SASES_CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def _chrome():
    for p in CHROME_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _check_url(url):
    if not url.startswith(ALLOWED):
        raise ValueError("只允许本地 8001 端口")
    return url


def _run_chrome(args, timeout=20):
    chrome = _chrome()
    if not chrome:
        raise RuntimeError("Chrome/Chromium 不可用")
    with tempfile.TemporaryDirectory(prefix="sases_ui_") as profile:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--user-data-dir=" + profile,
               "--virtual-time-budget=8000"] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=timeout, env=dict(os.environ))


def _dom(url):
    r = _run_chrome(["--dump-dom", url])
    return r.stdout or ""


def _count_selector(html, selector):
    selector = selector.strip()
    if not selector:
        return 0
    if selector.startswith("#"):
        return len(re.findall(r'id\s*=\s*["\']' + re.escape(selector[1:]) + r'["\']', html))
    if selector.startswith("."):
        cls = re.escape(selector[1:])
        return len(re.findall(r'class\s*=\s*["\'][^"\']*\b' + cls + r'\b[^"\']*["\']', html))
    if selector.startswith("["):
        # 简单属性选择器 [name=value]
        m = re.match(r"\[([\w-]+)\s*=\s*['\"]?([^'\"\]]+)['\"]?\]", selector)
        if m:
            return len(re.findall(r'\b' + re.escape(m.group(1)) + r'\s*=\s*["\']' + re.escape(m.group(2)) + r'["\']', html))
    return len(re.findall(r"<" + re.escape(selector) + r"[\s>]", html, re.I))


def run(params):
    action = (params.get("action") or "screenshot").lower()
    url = _check_url(params.get("url") or "http://127.0.0.1:8001/")
    result = {"success": True, "action": action, "url": url, "engine": "chrome-cli"}
    try:
        if not _chrome():
            raise RuntimeError("Chrome/Chromium 不可用")
        if action == "screenshot":
            os.makedirs(SHOT_DIR, exist_ok=True)
            fname = str(params.get("filename") or "shot.png")
            if not fname.lower().endswith(".png"):
                fname += ".png"
            fpath = os.path.join(SHOT_DIR, os.path.basename(fname))
            r = _run_chrome(["--window-size=1400,900", "--screenshot=" + fpath, url])
            if not os.path.isfile(fpath) or os.path.getsize(fpath) == 0:
                raise RuntimeError((r.stderr or "screenshot failed")[:500])
            result["file"] = "/static/_ui_shots/" + os.path.basename(fpath)
            result["bytes"] = os.path.getsize(fpath)
        elif action == "check_element":
            selector = params.get("selector", "")
            if not selector:
                raise ValueError("check_element 需要 selector")
            n = _count_selector(_dom(url), selector)
            result["selector"] = selector
            result["exists"] = n > 0
            result["count"] = n
            result["success"] = n > 0
        elif action == "check_text":
            text = str(params.get("text") or "")
            if not text:
                raise ValueError("check_text 需要 text")
            result["text"] = text
            result["exists"] = text in _dom(url)
            result["success"] = bool(result["exists"])
        else:
            raise ValueError("不支持的 action: " + action)
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result
