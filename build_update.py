#!/usr/bin/env python3
"""Build the hot-update bundle and manifest used by client_updater."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.client_release import build, _sha256

DEFAULT_OUT = r"D:\sases_build\client_update.zip"
DEFAULT_MANIFEST = r"D:\sases_build\client_version.json"
BASE_URL = "http://120.77.136.90:8001/static/downloads"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=None)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    local_version = {}
    path = ROOT / "client_version.json"
    if path.exists():
        local_version = json.loads(path.read_text(encoding="utf-8-sig"))
    version = args.version or local_version.get("version") or "1.0.0"
    build_id = time.strftime("%Y%m%d%H%M%S")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    build(str(ROOT), args.out, version, build_id)
    size = os.path.getsize(args.out)
    if size > 10 * 1024 * 1024:
        raise SystemExit(f"update bundle too large: {size} bytes")

    manifest = {
        "channel": "test",
        "version": version,
        "build": build_id,
        "min_version": "0.0.0",
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "package_url": args.base_url.rstrip("/") + "/" + os.path.basename(args.out),
        "sha256": _sha256(args.out),
        "size": size,
        "notes": "client update",
    }
    with open(args.manifest, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
