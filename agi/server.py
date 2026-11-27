"""Local-only HTTP control surface for the main AGI.

The main AGI is a separate process from the SASES service.  This server binds
to loopback and is intentionally tiny: health, observe, event ingestion.
"""
from __future__ import annotations

import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .protocol import Message
from .runtime import MainAGI

HOST = os.environ.get("SASES_AGI_BIND", "127.0.0.1")
PORT = int(os.environ.get("SASES_AGI_PORT", "8099"))
TOKEN_FILE = Path(os.environ.get("SASES_AGI_TOKEN_FILE", str(Path("data") / "agi.token")))


def _load_token() -> str:
    token = os.environ.get("SASES_AGI_TOKEN", "").strip()
    if token:
        return token
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    token = secrets.token_hex(24)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return token


class Handler(BaseHTTPRequestHandler):
    agi: MainAGI
    token: str

    def _send(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth(self) -> bool:
        return self.headers.get("X-SASES-AGI-Token", "") == self.token

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, "service": "main-agi", "db": self.agi.db_path})
            return
        if not self._auth():
            self._send(401, {"error": "unauthorized"})
            return
        if self.path.startswith("/agents"):
            from . import agents
            import sqlite3
            conn = sqlite3.connect(self.agi.db_path)
            conn.row_factory = sqlite3.Row
            try:
                self._send(200, {"agents": agents.list_agents(conn)})
            finally:
                conn.close()
            return
        if self.path.startswith("/escalations"):
            from . import escalation
            import sqlite3
            conn = sqlite3.connect(self.agi.db_path)
            try:
                self._send(200, {"escalations": escalation.list_open(conn)})
            finally:
                conn.close()
            return
        if self.path.startswith("/leader"):
            from urllib.parse import parse_qs, urlparse
            from . import leader
            scope = parse_qs(urlparse(self.path).query).get("scope", ["local"])[0]
            import sqlite3
            conn = sqlite3.connect(self.agi.db_path)
            try:
                self._send(200, {"leader": leader.status(conn, scope)})
            finally:
                conn.close()
            return
        if self.path.startswith("/nodes"):
            import sqlite3
            conn = sqlite3.connect(self.agi.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM agi_nodes ORDER BY last_seen DESC").fetchall()
            conn.close()
            self._send(200, {"nodes": [dict(r) for r in rows]})
            return
        if self.path.startswith("/events"):
            limit = int(parse_qs(urlparse(self.path).query).get("limit", ["50"])[0])
            import sqlite3
            conn = sqlite3.connect(self.agi.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id,node_id,type,severity,message,created_at FROM agi_events ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
            conn.close()
            self._send(200, {"events": [dict(r) for r in rows]})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._auth():
            self._send(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if self.path.startswith("/leader/"):
                from . import leader
                import sqlite3
                action = self.path.rsplit("/", 1)[-1]
                scope = str(body.get("scope") or "local")
                owner = str(body.get("owner") or "")
                ttl = int(body.get("ttl") or 60)
                if not owner:
                    self._send(400, {"error": "owner is required"})
                    return
                conn = sqlite3.connect(self.agi.db_path)
                try:
                    if action == "acquire":
                        ok = leader.acquire(conn, scope, owner, ttl)
                    elif action == "renew":
                        ok = leader.renew(conn, scope, owner, ttl)
                    elif action == "release":
                        ok = leader.release(conn, scope, owner)
                    else:
                        self._send(404, {"error": "not found"})
                        return
                    current = leader.status(conn, scope)
                finally:
                    conn.close()
                self._send(200 if ok else 409, {"ok": ok, "leader": current})
                return
            if self.path.startswith("/agents/"):
                from . import agents
                import sqlite3
                action = self.path.rsplit("/", 1)[-1]
                conn = sqlite3.connect(self.agi.db_path)
                conn.row_factory = sqlite3.Row
                try:
                    if action == "execute":
                        from .executor import execute
                        from .package import TaskPackage
                        package = TaskPackage(**body.get("package", {}))
                        agent_id = str(body.get("agent_id") or "")
                        if agent_id:
                            agents.lease(conn, agent_id, str(body.get("owner") or "main"), int(body.get("ttl") or 60))
                        result = execute(package, self.agi.registry, conn,
                                         owner=str(body.get("owner") or "main"),
                                         profile=str(body.get("profile") or "sub"))
                        if agent_id:
                            agents.finish(conn, agent_id, "done" if result.get("ok") else "failed")
                        self._send(200, result)
                        return
                    if action == "spawn":
                        agent_id = agents.spawn(
                            conn, str(body.get("node_id") or "local"),
                            body.get("task") or {}, str(body.get("role") or "sub"),
                            str(body.get("parent_run_id") or ""), int(body.get("ttl") or 300),
                        )
                        self._send(200, {"ok": True, "agent_id": agent_id})
                        return
                    agent_id = str(body.get("agent_id") or "")
                    if action == "lease":
                        ok = agents.lease(conn, agent_id, str(body.get("owner") or "main"),
                                          int(body.get("ttl") or 60))
                    elif action == "heartbeat":
                        ok = agents.heartbeat(conn, agent_id, str(body.get("owner") or "main"),
                                              int(body.get("ttl") or 60))
                    elif action == "finish":
                        ok = agents.finish(conn, agent_id, str(body.get("status") or "done"))
                    else:
                        self._send(404, {"error": "not found"})
                        return
                    self._send(200 if ok else 409, {"ok": ok})
                    return
                finally:
                    conn.close()
            if self.path == "/events":
                allowed = {k: body[k] for k in ("type", "node_id", "scope", "severity", "payload",
                                                "evidence", "requires_approval", "idempotency_key",
                                                "msg_id", "trace_id", "run_id", "parent_run_id",
                                                "created_at") if k in body}
                message = Message(**allowed)
                message.validate()
                self.agi.record_event(message)
                import sqlite3
                conn = sqlite3.connect(self.agi.db_path)
                health = "error" if message.severity in ("error", "critical") else "ok"
                version = str(message.payload.get("version") or "")
                conn.execute(
                    "INSERT INTO agi_nodes(node_id,scope,kind,role,version,health,last_seen) VALUES(?,?,?,?,?,?,?) "
                    "ON CONFLICT(node_id) DO UPDATE SET scope=excluded.scope,kind=excluded.kind,role=excluded.role,"
                    "version=excluded.version,health=excluded.health,last_seen=excluded.last_seen",
                    (message.node_id, message.scope, message.kind, "sub" if message.scope == "fleet" else "main",
                     version, health, message.created_at),
                )
                conn.commit()
                if message.severity == "critical":
                    from . import escalation
                    escalation.create(
                        conn, message.node_id,
                        str(message.payload.get("message") or "critical event"),
                        evidence=json.dumps(message.evidence, ensure_ascii=False),
                    )
                conn.close()
                self._send(200, {"ok": True, "msg_id": message.msg_id})
                return
            if self.path == "/observe":
                self._send(200, self.agi.run_once())
                return
            if self.path == "/ask":
                from .ask import answer
                self._send(200, answer(str(body.get("text") or ""), self.agi.db_path))
                return
            self._send(404, {"error": "not found"})
        except Exception as exc:  # noqa: BLE001
            self._send(400, {"error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt: str, *args) -> None:
        return


def serve() -> None:
    token = _load_token()
    Handler.token = token
    Handler.agi = MainAGI()
    print(json.dumps({"service": "main-agi", "bind": HOST, "port": PORT,
                      "db": Handler.agi.db_path, "token_file": str(TOKEN_FILE)}), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    serve()
