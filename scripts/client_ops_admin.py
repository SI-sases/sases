#!/usr/bin/env python3
"""SASES client operations admin CLI."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import client_ops


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("enqueue")
    p.add_argument("--node-id", required=True)
    p.add_argument("--action", required=True)
    p.add_argument("--payload", default="{}")
    p.add_argument("--requested-by", type=int, default=None)
    p.add_argument("--idempotency-key", default=None)

    p = sub.add_parser("list")
    p.add_argument("--node-id", default=None)
    p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    if args.command == "enqueue":
        payload = json.loads(args.payload)
        print(json.dumps(client_ops.enqueue(
            args.node_id, args.action, payload, args.requested_by, args.idempotency_key
        ), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(client_ops.list_operations(args.node_id, args.limit), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
