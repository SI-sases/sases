"""Track and forcibly terminate browser subprocesses by local agent id."""
from __future__ import annotations

import subprocess
import threading

_lock = threading.Lock()
_procs: dict[str, subprocess.Popen] = {}


def register(agent_id: str, proc: subprocess.Popen) -> None:
    if not agent_id:
        return
    with _lock:
        _procs[agent_id] = proc


def unregister(agent_id: str, proc: subprocess.Popen | None = None) -> None:
    if not agent_id:
        return
    with _lock:
        current = _procs.get(agent_id)
        if current is not None and (proc is None or current is proc):
            _procs.pop(agent_id, None)


def kill(agent_id: str) -> bool:
    if not agent_id:
        return False
    with _lock:
        proc = _procs.get(agent_id)
    if not proc:
        return False
    try:
        proc.kill()
        return True
    except Exception:
        return False
