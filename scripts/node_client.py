#!/usr/bin/env python3
"""Reference SASES node-aware client.

Loads a pilot bundle (wg_conf + Ed25519 key + manifest), sends the signed
manifest on every request and refreshes it with the user's JWT.

This is the contract the desktop/client code should implement.
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx


class NodeClient:
    def __init__(self, bundle_path: str, base_url: str = "http://10.10.0.1:8001"):
        with open(bundle_path, encoding="utf-8") as handle:
            self.bundle = json.load(handle)
        self.base_url = base_url.rstrip("/")
        self.token = ""
        self.manifest = self.bundle.get("manifest", "")
        self.node_id = self.bundle.get("node_id", "")
        self.http = httpx.Client(timeout=20, trust_env=False)

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if self.manifest:
            headers["X-SASES-Node-Manifest"] = self.manifest
        if extra:
            headers.update(extra)
        return headers

    def login(self, username: str, password: str) -> dict:
        response = self.http.post(
            self.base_url + "/auth/login",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        self.token = data.get("access_token") or data.get("token") or ""
        if not self.token:
            raise RuntimeError("login response has no access token")
        self.refresh_manifest()
        return data

    def refresh_manifest(self) -> dict:
        response = self.http.get(
            self.base_url + "/node/manifest",
            params={"node_id": self.node_id},
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()
        self.manifest = data["manifest"]
        self.bundle["manifest"] = self.manifest
        return data

    def request(self, method: str, path: str, **kwargs):
        response = self.http.request(
            method,
            self.base_url + path,
            headers=self._headers(kwargs.pop("headers", None)),
            **kwargs,
        )
        return response

    def whoami(self) -> dict:
        response = self.request("GET", "/node/whoami")
        response.raise_for_status()
        return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--base", default="http://10.10.0.1:8001")
    parser.add_argument("--username")
    parser.add_argument("--password")
    args = parser.parse_args()

    client = NodeClient(args.bundle, args.base)
    if args.username and args.password:
        client.login(args.username, args.password)
    print(json.dumps(client.whoami(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
