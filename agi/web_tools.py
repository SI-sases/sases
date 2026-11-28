"""Small read-only web tools for the main AGI."""
from __future__ import annotations

import ipaddress
import re
import socket
import ssl
import urllib.parse
import urllib.request


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _check_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("only http/https URLs are allowed")
    host = parsed.hostname.lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("local URLs are not allowed")
    try:
        ips = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise ValueError(f"DNS failed: {exc}") from exc
    for ip in ips:
        addr = ipaddress.ip_address(ip)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise ValueError("private network URLs are not allowed")
    return url


def fetch(args: dict) -> dict:
    try:
        url = _check_url(str(args.get("url") or ""))
        limit = max(1, min(int(args.get("max_bytes") or 200000), 1_000_000))
        req = urllib.request.Request(url, headers={"User-Agent": "SASES-AGI/1.0"})
        with urllib.request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
            raw = resp.read(limit + 1)
            text = raw[:limit].decode("utf-8", errors="replace")
            return {"ok": True, "url": resp.geturl(), "status": resp.status,
                    "text": text, "truncated": len(raw) > limit}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def search(args: dict) -> dict:
    try:
        query = str(args.get("query") or "").strip()
        if not query:
            return {"ok": False, "error": "query is required"}
        count = max(1, min(int(args.get("count") or 5), 10))
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SASES-AGI"})
        with urllib.request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
            html = resp.read(500_000).decode("utf-8", errors="replace")
        links = []
        for href, title in re.findall(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            title = re.sub(r"<[^>]+>", "", title).strip()
            links.append({"title": title[:200], "url": href})
            if len(links) >= count:
                break
        return {"ok": True, "query": query, "results": links}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
