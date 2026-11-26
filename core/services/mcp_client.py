"""Minimal MCP client for SASES.

Supports stdio MCP servers (JSON-RPC over stdin/stdout). Each operation opens a
short-lived session so a broken server cannot keep the app process alive.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from typing import Any

from core.db import db_cursor

PROTOCOL = "2024-11-05"


def ensure_schema() -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                transport TEXT NOT NULL DEFAULT 'stdio',
                command TEXT NOT NULL,
                args_json TEXT NOT NULL DEFAULT '[]',
                env_json TEXT NOT NULL DEFAULT '{}',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                input_schema TEXT NOT NULL DEFAULT '{}',
                cached_at TEXT NOT NULL,
                UNIQUE(server_id, name)
            )
            """
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _public(server: dict) -> dict:
    out = {k: v for k, v in server.items() if k != "env"}
    out["env_keys"] = sorted((server.get("env") or {}).keys())
    return out


def add_server(name: str, command: str, args: list[str], env: dict | None = None) -> dict:
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO mcp_servers(name,transport,command,args_json,env_json,enabled,created_at) VALUES (?,?,?,?,?,1,?)",
            (name, "stdio", command, json.dumps(args), json.dumps(env or {}), _now()),
        )
        server_id = cur.lastrowid
    return _public(get_server(server_id))


def get_server(server_id: int) -> dict:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute("SELECT id,name,transport,command,args_json,env_json,enabled,created_at FROM mcp_servers WHERE id=?", (server_id,))
        row = cur.fetchone()
    if not row:
        raise KeyError("mcp server not found")
    return {
        "id": row[0], "name": row[1], "transport": row[2], "command": row[3],
        "args": json.loads(row[4] or "[]"), "env": json.loads(row[5] or "{}"),
        "enabled": bool(row[6]), "created_at": row[7],
    }


def list_servers() -> list[dict]:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM mcp_servers ORDER BY id")
        ids = [r[0] for r in cur.fetchall()]
    return [_public(get_server(i)) for i in ids]


def remove_server(server_id: int) -> None:
    ensure_schema()
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM mcp_tools WHERE server_id=?", (server_id,))
        cur.execute("DELETE FROM mcp_servers WHERE id=?", (server_id,))


def _session(server: dict):
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in (server.get("env") or {}).items()})
    proc = subprocess.Popen(
        [server["command"], *[str(a) for a in server.get("args", [])]],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", env=env,
    )
    return proc


def _send(proc, payload: dict) -> None:
    proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    proc.stdin.flush()


def _recv(proc, timeout: float = 20.0) -> dict:
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    try:
        line = proc.stdout.readline()
    finally:
        timer.cancel()
    if not line:
        err = ""
        try:
            err = proc.stderr.read(500)
        except Exception:
            pass
        raise RuntimeError("MCP server closed" + (": " + err if err else ""))
    return json.loads(line)


def _rpc(proc, msg_id: int, method: str, params: dict | None = None) -> dict:
    _send(proc, {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
    while True:
        msg = _recv(proc)
        if msg.get("id") == msg_id:
            if "error" in msg:
                raise RuntimeError(str(msg["error"]))
            return msg.get("result") or {}


def _open(server: dict):
    proc = _session(server)
    try:
        init = _rpc(proc, 1, "initialize", {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "sases", "version": "1.0.0"}})
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        return proc, init
    except Exception:
        proc.kill()
        raise


def list_tools(server_id: int) -> list[dict]:
    server = get_server(server_id)
    if not server["enabled"]:
        raise RuntimeError("MCP server disabled")
    proc, _ = _open(server)
    try:
        result = _rpc(proc, 2, "tools/list")
        tools = result.get("tools", [])
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM mcp_tools WHERE server_id=?", (server_id,))
            for tool in tools:
                cur.execute(
                    "INSERT OR REPLACE INTO mcp_tools(server_id,name,description,input_schema,cached_at) VALUES (?,?,?,?,?)",
                    (server_id, tool.get("name", ""), tool.get("description", ""),
                     json.dumps(tool.get("inputSchema", {}), ensure_ascii=False), _now()),
                )
        return tools
    finally:
        proc.kill()


def call_tool(server_id: int, tool: str, arguments: dict | None = None) -> dict:
    server = get_server(server_id)
    if not server["enabled"]:
        raise RuntimeError("MCP server disabled")
    proc, _ = _open(server)
    try:
        result = _rpc(proc, 3, "tools/call", {"name": tool, "arguments": arguments or {}})
        return result
    finally:
        proc.kill()


def test_server(server_id: int) -> dict:
    tools = list_tools(server_id)
    return {"ok": True, "server_id": server_id, "tools": len(tools)}


def get_tool_meta(server_id: int, tool: str) -> dict | None:
    ensure_schema()
    with db_cursor() as cur:
        cur.execute(
            "SELECT name,description,input_schema FROM mcp_tools WHERE server_id=? AND name=?",
            (server_id, tool),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {"name": row[0], "description": row[1], "input_schema": json.loads(row[2] or "{}")}
