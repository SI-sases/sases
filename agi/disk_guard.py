"""Disk-space guard for local browser work.

The local browser and screenshot pipeline can fill a Windows temp drive. This
module frees only disposable files (old snapshots and old temp files) and
refuses a browser task when the drive is still too full.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

from .browser_snapshot import cleanup as cleanup_snapshots


class DiskFullError(RuntimeError):
    pass


def free_gb(path: str | Path = "C:\\") -> float:
    try:
        usage = shutil.disk_usage(str(path))
        return usage.free / (1024 ** 3)
    except OSError:
        return 0.0


def cleanup_temp(max_age_hours: int = 24) -> int:
    root = Path(tempfile.gettempdir())
    if not root.is_dir():
        return 0
    cutoff = time.time() - max(1, max_age_hours) * 3600
    removed = 0
    for path in root.rglob("*"):
        try:
            if not path.is_file() or path.stat().st_mtime >= cutoff:
                continue
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed


def ensure_free(min_gb: float = 1.0, path: str | Path = "C:\\") -> float:
    free = free_gb(path)
    if free >= min_gb:
        return free
    cleanup_snapshots()
    cleanup_temp(24)
    free = free_gb(path)
    if free < min_gb:
        raise DiskFullError(f"only {free:.2f} GB free; need {min_gb:.2f} GB")
    return free
