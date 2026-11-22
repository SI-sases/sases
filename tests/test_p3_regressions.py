import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.file_gate import check_frontend
from core.services.scheduled_task_service import _backoff_next


def test_file_gate_rejects_duplicate_id(tmp_path):
    p = tmp_path / "x.js"
    p.write_text('<div id="a"></div><div id="a"></div>', encoding="utf-8")
    r = check_frontend(str(p))
    assert r["ok"] is False
    assert "a" in r["error"]


def test_file_gate_allows_unique(tmp_path):
    p = tmp_path / "x.js"
    p.write_text('<div id="a"></div><div id="b"></div>', encoding="utf-8")
    assert check_frontend(str(p))["ok"] is True


def test_file_gate_ignores_non_frontend(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("x = 1\n", encoding="utf-8")
    assert check_frontend(str(p))["ok"] is True


def test_backoff_grows():
    from datetime import datetime
    a = datetime.fromisoformat(_backoff_next(0))
    b = datetime.fromisoformat(_backoff_next(3))
    assert (b - a).total_seconds() > 0
    assert (b - datetime.now()).total_seconds() <= 3600


def test_goal_runner_imports_without_cycle():
    from core.services import goal_runner
    assert callable(goal_runner.run_goal_round)
