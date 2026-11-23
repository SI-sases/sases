#!/usr/bin/env python3
"""Summarize node permission shadow/denied audit events."""
from __future__ import annotations

import os
import sqlite3
import sys

DB = os.environ.get("SASES_DB_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users.db"
)


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    print("last 24h by result")
    for row in conn.execute(
        "select result, count(*) as n from identity_audit "
        "where created_at >= datetime('now','-1 day') group by result order by n desc"
    ):
        print(f"  {row['result']}: {row['n']}")
    print("recent shadow/denied")
    for row in conn.execute(
        "select action, result, detail, node_id, user_id, created_at from identity_audit "
        "where result in ('shadow','denied') order by id desc limit 20"
    ):
        print(f"  {row['created_at']} {row['action']} {row['result']} {row['detail']} node={row['node_id']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
