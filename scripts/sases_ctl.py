#!/usr/bin/env python3
"""SASES Control: minimal CLI for agents to operate SASES HQ.

Environment:
  SASES_HQ_URL   default http://127.0.0.1:8001
  SASES_HQ_TOKEN JWT for user actions
  SASES_LINK_TOKEN shared token for executor actions
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

HQ = os.environ.get("SASES_HQ_URL", "http://127.0.0.1:8001").rstrip("/")
TOKEN = os.environ.get("SASES_HQ_TOKEN", "")
LINK_TOKEN = os.environ.get("SASES_LINK_TOKEN", "")


def headers() -> dict:
    out = {"Content-Type": "application/json"}
    if TOKEN:
        out["Authorization"] = f"Bearer {TOKEN}"
    elif LINK_TOKEN:
        out["X-SASES-Link-Token"] = LINK_TOKEN
    return out


def client() -> httpx.Client:
    return httpx.Client(base_url=HQ, headers=headers(), timeout=20, trust_env=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Control SASES HQ")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("campaigns", help="list campaigns")
    p = sub.add_parser("create", help="create a campaign")
    p.add_argument("--name", required=True)
    p.add_argument("--region", default="cn")
    p.add_argument("--platform", action="append", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--manual", action="store_true")
    p = sub.add_parser("approve", help="approve a campaign")
    p.add_argument("campaign_id", type=int)
    sub.add_parser("tasks", help="list tasks")
    p = sub.add_parser("claim", help="claim one task")
    p.add_argument("--platform", default=None)
    p.add_argument("--manual", action="store_true")
    p.add_argument("--no-manual", action="store_true")
    p = sub.add_parser("receipt", help="post a receipt")
    p.add_argument("task_id", type=int)
    p.add_argument("--status", default="done")
    p.add_argument("--url", default="")
    p.add_argument("--error", default="")
    p = sub.add_parser("cancel", help="cancel a task without retry")
    p.add_argument("task_id", type=int)
    p.add_argument("--reason", default="cancelled by operator")

    args = parser.parse_args()
    with client() as c:
        if args.cmd == "campaigns":
            r = c.get("/hq/campaigns")
        elif args.cmd == "create":
            r = c.post("/hq/campaigns", json={
                "name": args.name,
                "region": args.region,
                "platforms": args.platform,
                "content": {"title": args.title, "body": args.body, "manual": bool(args.manual)},
            })
        elif args.cmd == "approve":
            r = c.post(f"/hq/campaigns/{args.campaign_id}/approve")
        elif args.cmd == "tasks":
            r = c.get("/hq/tasks")
        elif args.cmd == "claim":
            params = {}
            if args.platform:
                params["platform"] = args.platform
            if args.manual:
                params["manual"] = "true"
            elif args.no_manual:
                params["manual"] = "false"
            r = c.post("/hq/tasks/claim", params=params or None)
        elif args.cmd == "cancel":
            r = c.post(f"/hq/tasks/{args.task_id}/cancel", params={"reason": args.reason})
        elif args.cmd == "receipt":
            r = c.post(f"/hq/tasks/{args.task_id}/receipt", json={
                "status": args.status,
                "result": {"ok": args.status == "done", "url": args.url},
                "error": args.error or None,
            })
        else:
            return 2
    print(json.dumps({"status": r.status_code, "body": r.text}, ensure_ascii=False, indent=2))
    return 0 if r.status_code < 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
