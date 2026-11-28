"""Detect a practical local worker count from CPU and memory.

Browser tasks are still serialized by LocalRuntime.browser_lock.  This value
sizes the non-browser session pool; it is not a fixed two-worker cap.
"""
from __future__ import annotations

import ctypes
import os


def total_memory_gb() -> float:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys / (1024 ** 3)
        return 0.0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
    except (AttributeError, ValueError, OSError):
        return 0.0


def detect() -> dict:
    cpu = os.cpu_count() or 2
    memory = total_memory_gb()
    cpu_slots = max(2, cpu * 2)
    memory_slots = max(2, int(memory / 0.75)) if memory else cpu_slots
    workers = max(2, min(cpu_slots, memory_slots))
    return {
        "workers": workers,
        "cpu": cpu,
        "memory_gb": round(memory, 1),
        "cpu_slots": cpu_slots,
        "memory_slots": memory_slots,
    }
