"""Human-readable report from the main AGI store."""
from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path


def generate(db_path: str) -> str:
    from .runtime import ensure_schema
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    nodes = conn.execute(
        "SELECT node_id,scope,kind,role,version,health,last_seen FROM agi_nodes ORDER BY scope,node_id"
    ).fetchall()
    events = conn.execute(
        "SELECT node_id,type,severity,message,created_at FROM agi_events "
        "WHERE severity IN ('error','critical') ORDER BY id DESC LIMIT 10"
    ).fetchall()
    leader = conn.execute("SELECT scope,owner,expires_at FROM agi_leader").fetchall()
    try:
        escalations = conn.execute(
            "SELECT id,node_id,reason,severity,created_at FROM agi_escalations "
            "WHERE status='open' ORDER BY id DESC LIMIT 20"
        ).fetchall()
    except sqlite3.OperationalError:
        escalations = []
    conn.close()

    lines = ["# SASES 主 AGI 汇报", "", f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", "", "## 节点"]
    if not nodes:
        lines.append("- 暂无节点")
    for n in nodes:
        lines.append(
            f"- `{n['node_id']}` scope={n['scope']} kind={n['kind']} role={n['role']} "
            f"health={n['health']} version={n['version'] or '-'}"
        )
    lines += ["", "## Leader"]
    if not leader:
        lines.append("- 无")
    for row in leader:
        lines.append(f"- scope={row['scope']} owner={row['owner']} expires={row['expires_at']}")
    lines += ["", "## 最近错误"]
    if not events:
        lines.append("- 无")
    for e in events:
        lines.append(f"- {e['created_at']} `{e['node_id']}` {e['severity']} {e['message']}")
    lines += ["", "## 需要指挥官处理"]
    if not escalations:
        lines.append("- 无")
    for item in escalations:
        lines.append(
            f"- #{item['id']} `{item['node_id']}` {item['severity']} {item['reason']}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/agi.db")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    text = generate(args.db)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
