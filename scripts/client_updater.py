#!/usr/bin/env python3
"""SASES client hot updater.

Downloads a signed-by-hash update bundle, verifies SHA256, and atomically
replaces only code directories. User data (users.db/.env/data/uploads) is
never touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.request
import zipfile
from urllib.parse import urljoin

DEFAULT_MANIFEST_URLS = [
    "https://github.com/SI-sases/sases/releases/latest/download/client_version.json",
    "http://120.77.136.90:8001/static/downloads/client_version.json",
]
_env_urls = os.getenv("SASES_CLIENT_UPDATE_URL", "").strip()
if _env_urls:
    DEFAULT_MANIFEST_URLS = [u.strip() for u in _env_urls.split(",") if u.strip()]
ALLOWED_ROOTS = ("core", "static", "scripts", "launcher", "wireguard")
EXCLUDED_PARTS = {"__pycache__", ".git", "build", "dist", "node_modules"}


class UpdateError(Exception):
    pass


def _version_tuple(value: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", value or "")) or (0,)


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def local_version(root: str) -> dict:
    for name in ("client_version.json", "version.json"):
        path = os.path.join(root, name)
        if os.path.exists(path):
            try:
                data = _read_json(path)
                return {"version": str(data.get("version") or ""), "build": str(data.get("build") or ""), "raw": data}
            except Exception:
                pass
    return {"version": "", "build": "", "raw": {}}


def fetch_manifest(urls=None) -> tuple[dict, str]:
    errors = []
    for url in urls or DEFAULT_MANIFEST_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SASES-Updater"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not data.get("version") or not data.get("package_url"):
                raise UpdateError("manifest missing version/package_url")
            return data, url
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise UpdateError("no update manifest reachable: " + " | ".join(errors))


def is_newer(remote: dict, local: dict) -> bool:
    rv = _version_tuple(remote.get("version", ""))
    lv = _version_tuple(local.get("version", ""))
    if rv != lv:
        return rv > lv
    return bool(remote.get("build") and remote.get("build") != local.get("build"))


def download(url: str, expected_sha: str, expected_size: int | None, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "SASES-Updater"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    digest = hashlib.sha256()
    total = 0
    with opener.open(req, timeout=60) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            digest.update(chunk)
            total += len(chunk)
    if expected_size and total != int(expected_size):
        raise UpdateError(f"size mismatch: {total} != {expected_size}")
    actual = digest.hexdigest()
    if expected_sha and actual.lower() != str(expected_sha).lower():
        raise UpdateError(f"sha256 mismatch: {actual}")


def extract_safe(zip_path: str, staging: str) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            parts = [p for p in name.split("/") if p]
            if not parts or name.startswith("/") or ".." in parts:
                continue
            if parts[0] not in ALLOWED_ROOTS:
                continue
            if any(part in EXCLUDED_PARTS for part in parts):
                continue
            target = os.path.join(staging, *parts)
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def apply_update(root: str, manifest: dict, manifest_url: str) -> dict:
    package_url = urljoin(manifest_url, manifest["package_url"])
    staging = os.path.join(root, ".update_staging")
    backup_root = os.path.join(root, ".update_backup", time.strftime("%Y%m%d_%H%M%S"))
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)
    os.makedirs(backup_root, exist_ok=True)

    zip_path = os.path.join(staging, "update.zip")
    download(package_url, manifest.get("sha256", ""), manifest.get("size"), zip_path)
    extract_safe(zip_path, staging)

    moved = []
    try:
        for name in ALLOWED_ROOTS:
            src = os.path.join(root, name)
            dst = os.path.join(backup_root, name)
            if os.path.exists(src):
                os.replace(src, dst)
                moved.append(name)
            new = os.path.join(staging, name)
            if os.path.exists(new):
                os.replace(new, src)
        with open(os.path.join(root, "client_version.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "version": manifest.get("version"),
                "build": manifest.get("build", ""),
                "channel": manifest.get("channel", "test"),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, handle, ensure_ascii=False, indent=2)
    except Exception:
        for name in ALLOWED_ROOTS:
            src = os.path.join(root, name)
            dst = os.path.join(backup_root, name)
            if os.path.exists(src):
                shutil.rmtree(src, ignore_errors=True)
            if os.path.exists(dst):
                os.replace(dst, src)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return {
        "version": manifest.get("version"),
        "build": manifest.get("build", ""),
        "backup": backup_root,
        "package_url": package_url,
    }


def check_and_apply(root: str, urls=None, apply: bool = True) -> dict:
    if os.getenv("SASES_CLIENT_UPDATE_DISABLE", "").strip().lower() in ("1", "true", "yes"):
        return {"updated": False, "disabled": True}
    local = local_version(root)
    manifest, manifest_url = fetch_manifest(urls)
    if not is_newer(manifest, local):
        return {"updated": False, "local": local.get("version"), "remote": manifest.get("version")}
    if not apply:
        return {"updated": False, "available": True, "local": local.get("version"), "remote": manifest.get("version")}
    result = apply_update(root, manifest, manifest_url)
    result["updated"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--manifest", action="append", help="manifest URL, repeatable")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check_and_apply(args.root, args.manifest, apply=not args.check)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
