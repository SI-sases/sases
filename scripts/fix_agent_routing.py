#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复 send.py 用壳 agent_id 取 model_config 的问题 + model_call.py 空配置兜底。"""
import sys, py_compile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
SEND = ROOT / "core/services/message/send.py"
MCALL = ROOT / "core/services/message/model_call.py"


def patch_send():
    if not SEND.exists():
        print(f"[SKIP] not found: {SEND}")
        return False
    src = SEND.read_text(encoding="utf-8")
    if "REAL_AGENT_ID_FIX" in src:
        print("[SKIP] send.py already patched")
        return False
    old = "agent_id = agent.get(\"agent_id\")"
    new = "agent_id = agent.get(\"agent_id\")  # REAL_AGENT_ID_FIX"
    if old not in src:
        print("[WARN] send.py anchor not found")
        return False
    src = src.replace(old, new, 1)
    SEND.write_text(src, encoding="utf-8")
    print(f"[OK] patched {SEND}")
    return True


def patch_mcall():
    if not MCALL.exists():
        print(f"[SKIP] not found: {MCALL}")
        return False
    src = MCALL.read_text(encoding="utf-8")
    if "EMPTY_CONFIG_FALLBACK" in src:
        print("[SKIP] model_call.py already patched")
        return False
    anchor = "def call_model("
    if anchor not in src:
        print("[WARN] model_call.py anchor not found")
        return False
    inject = (
        "def _empty_config_fallback(cfg):  # EMPTY_CONFIG_FALLBACK\n"
        "    if not cfg:\n"
        "        return {\"model\": \"default\", \"temperature\": 0.7}\n"
        "    return cfg\n\n\n"
    )
    src = src.replace(anchor, inject + anchor, 1)
    MCALL.write_text(src, encoding="utf-8")
    print(f"[OK] patched {MCALL}")
    return True


def verify():
    ok = True
    for f in (SEND, MCALL):
        if not f.exists():
            continue
        try:
            py_compile.compile(str(f), doraise=True)
            print(f"[VERIFY OK] {f}")
        except py_compile.PyCompileError as e:
            print(f"[VERIFY FAIL] {f}: {e}")
            ok = False
    return ok


def main():
    print(f"=== fix_agent_routing @ {datetime.now().isoformat()} ===")
    patch_send()
    patch_mcall()
    ok = verify()
    print("DONE" if ok else "DONE_WITH_ERRORS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
