"""UI 快照采集骨架：headless Chrome 截图。"""
import argparse
import os
import subprocess
import sys

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

PAGES = {
    "login": "/",
}


def chrome_path():
    for p in CHROME_CANDIDATES:
        if os.path.isfile(p):
            return p
    raise SystemExit("找不到 Chrome，请修改 CHROME_CANDIDATES")


def shot(url, out, size="1400,900"):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    profile = os.path.join(os.path.dirname(out), "_profile")
    cmd = [
        chrome_path(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--user-data-dir=" + profile, "--window-size=" + size,
        "--virtual-time-budget=15000", "--screenshot=" + out, url,
    ]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    ap.add_argument("--out", default="tests/ui/baseline")
    ap.add_argument("--pages", default="login")
    args = ap.parse_args()
    for name in args.pages.split(","):
        name = name.strip()
        if name not in PAGES:
            print("skip unknown page: " + name)
            continue
        out = os.path.join(args.out, name + ".png")
        shot(args.base + PAGES[name], out)
        print("captured " + out)


if __name__ == "__main__":
    main()
