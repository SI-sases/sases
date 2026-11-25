#!/usr/bin/env python3
"""SASES Link peer loop: pull messages and execute allowlisted actions."""
from __future__ import annotations

import json
import os
import sys
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BASE_URL = os.environ.get("SASES_LINK_BASE", "http://10.10.0.1:8001").rstrip("/")
IDENTITY = os.environ.get("SASES_LINK_IDENTITY") or os.path.join(ROOT, "node_identity.json")
TOKEN = os.environ.get("SASES_LINK_TOKEN", "")
SELF_NODE = os.environ.get("SASES_NODE_ID", "")
LOCK = os.environ.get("SASES_LINK_LOCK") or os.path.join(ROOT, ".link_agent." + str(abs(hash(IDENTITY))) + ".lock")


def _headers(identity):
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["X-SASES-Link-Token"] = TOKEN
    elif identity:
        headers["X-SASES-Node-Manifest"] = identity.get("manifest", "")
    return headers


def _acquire_lock():
    if os.path.exists(LOCK):
        try:
            if time.time() - os.path.getmtime(LOCK) < 120:
                return False
        except OSError:
            pass
    with open(LOCK, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return True


def _release_lock():
    try:
        os.remove(LOCK)
    except OSError:
        pass


def main():
    if not _acquire_lock():
        print("[link] another agent is running", flush=True)
        return 0
    try:
        identity = {}
        if os.path.isfile(IDENTITY):
            with open(IDENTITY, encoding="utf-8-sig") as handle:
                identity = json.load(handle)
        if not TOKEN and not identity:
            raise SystemExit("SASES_LINK_TOKEN or node_identity.json required")
        headers = _headers(identity)
        from scripts.client_ops_agent import _execute
        while True:
            try:
                resp = httpx.get(BASE_URL + "/link/inbox", headers=headers, params={"receiver": SELF_NODE or None}, timeout=15)
                if resp.status_code != 200:
                    print(f"[link] inbox {resp.status_code}", flush=True)
                    time.sleep(5)
                    continue
                for msg in resp.json().get("messages", []):
                    msg_id = msg["msg_id"]
                    action = msg.get("action", "")
                    try:
                        payload = json.loads(msg.get("payload") or "{}")
                    except Exception:
                        payload = {}
                    httpx.post(BASE_URL + "/link/ack", headers=headers,
                               json={"msg_id": msg_id, "status": "running"}, timeout=15)
                    try:
                        result = _execute(action, payload)
                        status = "done"
                    except Exception as exc:
                        result = {"error": str(exc)}
                        status = "failed"
                    httpx.post(BASE_URL + "/link/ack", headers=headers,
                               json={"msg_id": msg_id, "status": status, "result": result}, timeout=15)
                    print(f"[link] {msg_id} {action} -> {status}", flush=True)
            except Exception as exc:
                print(f"[link] loop error: {exc}", flush=True)
            time.sleep(3)
    finally:
        _release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
