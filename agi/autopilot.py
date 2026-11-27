"""Autopilot loop: observe, report, and keep a durable audit trail.

It intentionally does not mutate production.  Mutating tools remain gated.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .report import generate
from .runtime import MainAGI


def run_once(base_url: str, db_path: str, report_out: str = "") -> dict:
    result = MainAGI(base_url=base_url, db_path=db_path).run_once()
    report = generate(db_path)
    if report_out:
        Path(report_out).parent.mkdir(parents=True, exist_ok=True)
        Path(report_out).write_text(report, encoding="utf-8")
    return {"ok": result.get("ok"), "node_id": result.get("node_id"), "report": report}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--db", default="data/agi.db")
    parser.add_argument("--report-out", default="reports/agi_report.md")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        result = run_once(args.base_url, args.db, args.report_out)
        print(json.dumps({"ok": result["ok"], "node_id": result["node_id"]}, ensure_ascii=False))
        if args.once:
            return 0
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
