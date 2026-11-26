#!/usr/bin/env python3
"""Minimal MCP stdio server for SASES Control.

Protocol: JSON-RPC 2.0 over stdin/stdout.
Configure SASES_HQ_URL and SASES_HQ_TOKEN (or SASES_LINK_TOKEN).
"""
from __future__ import annotations

import json
import os
import sys

import httpx

HQ = os.environ.get("SASES_HQ_URL", "http://127.0.0.1:8001").rstrip("/")
TOKEN = os.environ.get("SASES_HQ_TOKEN", "")
LINK = os.environ.get("SASES_LINK_TOKEN", "")
PROTOCOL = "2024-11-05"


def headers() -> dict:
    h = {"Content-Type": "application/json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    elif LINK:
        h["X-SASES-Link-Token"] = LINK
    return h


def call(method: str, path: str, body: dict | None = None, params: dict | None = None) -> dict:
    with httpx.Client(base_url=HQ, headers=headers(), timeout=20, trust_env=False) as c:
        r = c.request(method, path, json=body, params=params)
    return {"status": r.status_code, "body": r.text}


TOOLS = [
    {
        "name": "sases_list_campaigns",
        "description": "List SASES HQ campaigns.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sases_create_campaign",
        "description": "Create a campaign. Approval is required before dispatch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "region": {"type": "string", "default": "cn"},
                "platforms": {"type": "array", "items": {"type": "string"}},
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["name", "platforms", "body"],
        },
    },
    {
        "name": "sases_approve_campaign",
        "description": "Approve a campaign and queue its tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {"campaign_id": {"type": "integer"}},
            "required": ["campaign_id"],
        },
    },
    {
        "name": "sases_list_tasks",
        "description": "List HQ tasks, optionally filtered by status.",
        "inputSchema": {"type": "object", "properties": {"status": {"type": "string"}}},
    },
]


def tool_call(name: str, args: dict) -> dict:
    if name == "sases_list_campaigns":
        return call("GET", "/hq/campaigns")
    if name == "sases_create_campaign":
        return call("POST", "/hq/campaigns", {
            "name": args["name"],
            "region": args.get("region", "cn"),
            "platforms": args["platforms"],
            "content": {"title": args.get("title", ""), "body": args["body"]},
        })
    if name == "sases_approve_campaign":
        return call("POST", f"/hq/campaigns/{int(args['campaign_id'])}/approve")
    if name == "sases_list_tasks":
        return call("GET", "/hq/tasks", params={"status": args.get("status")} if args.get("status") else None)
    return {"status": 404, "body": json.dumps({"error": "unknown tool"})}


def reply(msg_id, result=None, error=None) -> None:
    payload = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        payload["error"] = {"code": -32603, "message": str(error)}
    else:
        payload["result"] = result
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = request.get("method")
        msg_id = request.get("id")
        if method == "initialize":
            reply(msg_id, {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "sases-control", "version": "1.0.0"},
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = request.get("params") or {}
            try:
                result = tool_call(params.get("name", ""), params.get("arguments") or {})
                reply(msg_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]})
            except Exception as exc:
                reply(msg_id, error=f"{type(exc).__name__}: {exc}")
        elif msg_id is not None:
            reply(msg_id, error=f"unknown method: {method}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
