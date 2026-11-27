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
            if self.path == "/events":
                allowed = {k: body[k] for k in ("type", "node_id", "scope", "severity", "payload",
                                                "evidence", "requires_approval", "idempotency_key",
                                                "msg_id", "created_at") if k in body}
                message = Message(**allowed)
                message.validate()
                self.agi.record_event(message)
                self._send(200, {"ok": True, "msg_id": message.msg_id})
                return
            if self.path == "/observe":
                self._send(200, self.agi.run_once())
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
