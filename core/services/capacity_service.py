# core/services/capacity_service.py
# -*- coding: utf-8 -*-
"""按设备 CPU/内存给出并发上限；物理极限优先，配置只做减法。"""
import ctypes
import os
import threading


def _memory_gb():
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        st = MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            return round(st.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        pass
    try:
        return round(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024 ** 3), 1)
    except Exception:
        return 0.0


def profile():
    cpu = os.cpu_count() or 2
    mem = _memory_gb()
    # 读并发：CPU 一半、最多 3；内存 < 4G 再降 1
    read = max(1, min(3, cpu // 2))
    if mem and mem < 4:
        read = 1
    write = 1
    return {
        "cpu": cpu,
        "memory_gb": mem,
        "read_parallel": read,
        "write_parallel": write,
        "background_parallel": 1,
        "subagent_parallel": read,
    }


_PROFILE = profile()
_READ_SLOTS = threading.BoundedSemaphore(max(1, int(_PROFILE["read_parallel"])))


def acquire_subagent_slot(timeout=30):
    return _READ_SLOTS.acquire(timeout=timeout)


def release_subagent_slot():
    try:
        _READ_SLOTS.release()
    except ValueError:
        pass
