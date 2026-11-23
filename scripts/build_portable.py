#!/usr/bin/env python3
"""Build the full portable SASES client package.

Output is intentionally written outside the source tree to avoid recursively
including old packages from static/downloads.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import sys
import tarfile
import zipfile

ROOT_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = r"D:\sases_build\sases-portable.zip"
DEFAULT_STAGE = r"D:\sases_build\portable_stage"
DEFAULT_EMBED = r"D:\sases\python-embed"

ROOT_DIRS = ("core", "static", "harness_modules", "launcher", "scripts", "wireguard")
ROOT_FILES = (
    "app_full.py",
    "requirements.txt",
    "client_version.json",
    "SASES-start.bat",
    "LICENSE",
    "COMMERCIAL.md",
    "THIRD_PARTY_LICENSES.md",
)
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "build",
    "dist",
    "downloads",
    "_ui_shots",
    ".backups",
    ".update_backup",
    ".update_staging",
    "data",
    "node_modules",
    ".pytest_cache",
}
EXCLUDE_FILES = {
    "users.db",
    "users.db-wal",
    "users.db-shm",
    "remote_users.db",
    "remote_users.db-wal",
    "remote_users.db-shm",
    ".env",
    "local_run.out",
    "local_run.err",
    "remote_run.out",
    "remote_run.err",
    "runtime_port.json",
    "node_identity.json",
    "license.json",
}
# Optional heavy dependencies are not needed by the desktop client runtime.
EXCLUDE_PACKAGES = {
    "scipy",
    "scipy.libs",
    "sklearn",
    "chromadb",
    "chromadb_rust_bindings",
    "kubernetes",
    "grpc",
    "hf_xet",
    "tokenizers",
    "transformers",
    "huggingface_hub",
    "torch",
    "pandas",
    "pyarrow",
    "matplotlib",
    "playwright",
    "PyInstaller",
    "pytest",
    "_pytest",
    "pip",
}

BAT = """@echo off
cd /d %~dp0
if exist "python-embed\\pythonw.exe" (
  start "" "python-embed\\pythonw.exe" "launcher\\launcher.py"
) else if exist "python-embed\\python.exe" (
  start "" "python-embed\\python.exe" "launcher\\launcher.py"
) else (
  start "" python "launcher\\launcher.py"
)
"""


def _ignore(directory, names):
    ignored = []
    site_packages = os.path.basename(directory).lower() == "site-packages"
    for name in names:
        if name in EXCLUDE_DIRS or name in EXCLUDE_FILES:
            ignored.append(name)
        elif name.endswith(".pyc") or name.endswith(".pyo"):
            ignored.append(name)
        elif site_packages:
            stem = name.split("-")[0].split(".")[0]
            if name in EXCLUDE_PACKAGES or stem in EXCLUDE_PACKAGES:
                ignored.append(name)
    return ignored


def _remove(path: str) -> None:
    if not os.path.exists(path):
        return

    def _onerror(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:
            pass

    shutil.rmtree(path, onerror=_onerror)


def _copy_tree(src: str, dst: str) -> None:
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=False)


def _verify(zip_path: str) -> None:
    forbidden = ("users.db", ".env", "static/downloads", "sases_client", "code_update.zip")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for name in names:
        low = name.lower()
        if any(part in low for part in forbidden):
            raise SystemExit(f"forbidden file in package: {name}")
    required = ("python-embed/python.exe", "core/bootstrap.py", "launcher/launcher.py", "app_full.py")
    missing = [item for item in required if item not in names]
    if missing:
        raise SystemExit(f"missing required files: {missing}")
    print(f"[portable] verified {len(names)} files")


def build(root: str, out: str, stage: str, embed: str) -> None:
    if not os.path.isdir(embed):
        raise SystemExit(f"python-embed not found: {embed}")
    if not os.path.isfile(os.path.join(root, "launcher", "dist", "SASES启动器.exe")):
        raise SystemExit("SASES启动器.exe missing; run build_launcher_exe.py first")

    _remove(stage)
    os.makedirs(stage, exist_ok=True)
    _copy_tree(embed, os.path.join(stage, "python-embed"))

    for name in ROOT_DIRS:
        src = os.path.join(root, name)
        if os.path.isdir(src):
            _copy_tree(src, os.path.join(stage, name))
    for name in ROOT_FILES:
        src = os.path.join(root, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(stage, name))

    shutil.copy2(
        os.path.join(root, "launcher", "dist", "SASES启动器.exe"),
        os.path.join(stage, "SASES启动器.exe"),
    )
    with open(os.path.join(stage, "启动SASES.bat"), "w", encoding="utf-8") as handle:
        handle.write(BAT)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    shutil.make_archive(out[:-4], "zip", stage)
    _verify(out)
    xz_path = out[:-4] + ".tar.xz"
    with tarfile.open(xz_path, "w:xz", preset=6) as archive:
        for name in os.listdir(stage):
            archive.add(os.path.join(stage, name), arcname=name)
    digest = hashlib.sha256(open(out, "rb").read()).hexdigest()
    with open(out + ".sha256", "w", encoding="utf-8") as handle:
        handle.write(digest + "  " + os.path.basename(out) + "\n")
    xz_digest = hashlib.sha256(open(xz_path, "rb").read()).hexdigest()
    with open(xz_path + ".sha256", "w", encoding="utf-8") as handle:
        handle.write(xz_digest + "  " + os.path.basename(xz_path) + "\n")
    print(f"[portable] {out} {os.path.getsize(out) / 1024 / 1024:.1f} MB")
    print(f"[portable] {xz_path} {os.path.getsize(xz_path) / 1024 / 1024:.1f} MB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT_DEFAULT)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--stage", default=DEFAULT_STAGE)
    parser.add_argument("--python-embed", default=DEFAULT_EMBED)
    args = parser.parse_args()
    build(os.path.abspath(args.root), os.path.abspath(args.out), os.path.abspath(args.stage), os.path.abspath(args.python_embed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
