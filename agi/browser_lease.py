"""Keyed browser-profile leases.

The old runtime held one global browser lock. A lease is scoped to a Chrome
profile: the default profile stays serial, while separate profiles can run in
parallel when a deployment provides them.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager


class BrowserLeases:
    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock(self, profile: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(profile or "default", threading.Lock())

    @contextmanager
    def acquire(self, profile: str = "default"):
        lock = self._lock(profile)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    @staticmethod
    def profile_for(task: dict) -> str:
        return str(task.get("browser_profile") or "default")
