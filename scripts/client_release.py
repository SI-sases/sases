#!/usr/bin/env python3
"""Build a SASES client update bundle and manifest.

Example:
  python scripts/client_release.py --version 1.0.1-test --out dist/client_update.zip \
    --manifest dist/client_version.json --base-url http://120.77.136.90:8001/static/downloads/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import zipfile

ROOT_FILES = ("app_full.py", "requirements.txt", "boot_launcher.py")
ROOT_DIRS = ("core", "static", "scripts", "launcher", "wireguard")
EXCLUDE_DIRS = {"__pycache__", ".git", "build", "dist", "node_modules", ".pytest_cache", "downloads", "_ui_shots"}


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(root: str, out: str, version: str, build_id: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name in ROOT_FILES:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                zf.write(path, name)
        for dirname in ROOT_DIRS:
            base_dir = os.path.join(root, dirname)
            if not os.path.isdir(base_dir):
                continue
            for base, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for name in files:
                    path = os.path.join(base, name)
                    arc = os.path.relpath(path, root)
                    zf.write(path, arc)
    return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--version", required=True)
    parser.add_argument("--build", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--channel", default="test")
    parser.add_argument("--notes", default="")
    parser.add_argument("--min-version", default="0.0.0")
    args = parser.parse_args()

    build(args.root, args.out, args.version, args.build)
    filename = os.path.basename(args.out)
    manifest = {
        "channel": args.channel,
        "version": args.version,
        "build": args.build or time.strftime("%Y%m%d%H%M%S"),
        "min_version": args.min_version,
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "package_url": args.base_url.rstrip("/") + "/" + filename,
        "sha256": _sha256(args.out),
        "size": os.path.getsize(args.out),
        "notes": args.notes,
    }
    with open(args.manifest, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
