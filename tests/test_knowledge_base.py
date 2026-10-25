import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import knowledge_base
import core.db as db

@pytest.fixture
def temp_kb(tmp_path, monkeypatch):
    """使用临时数据库，避免污染真实数据"""
    db_file = tmp_path / "test_users.db"
    monkeypatch.setattr(db, "DB_FILE", str(db_file))
    db.init_db()
    # 清空知识库和共享日志，保证测试隔离
    with db.get_db() as conn:
        conn.execute("DELETE FROM kb_entries")
        conn.execute("DELETE FROM shared_pollinate_log")
    return knowledge_base

def test_add_and_load_kb(temp_kb):
    assert temp_kb.load_kb() == []

    temp_kb.add_to_kb(
        task="测试任务",
        branch_a="思路A",
        branch_b="思路B",
        synthesis="解决方案",
        model_id="test_model",
        user_id="user_1",
        backtrack_count=1,
        test_cases=[{"input": 1, "expected_output": 2}]
    )

    kb = temp_kb.load_kb()
    assert len(kb) == 1
    assert kb[0]["task"] == "测试任务"
    assert kb[0]["solution"] == "解决方案"
    assert kb[0]["model_id"] == "test_model"
    assert kb[0]["user_id"] == "user_1"
    assert kb[0]["backtrack_count"] == 1
    assert kb[0]["verified"] is True

def test_add_multiple_entries(temp_kb):
    temp_kb.add_to_kb(task="任务1", branch_a="", branch_b="", synthesis="方案1")
    temp_kb.add_to_kb(task="任务2", branch_a="", branch_b="", synthesis="方案2")
    kb = temp_kb.load_kb()
    assert len(kb) == 2
    assert kb[0]["task"] == "任务1"
    assert kb[1]["task"] == "任务2"

def test_shared_id_management(temp_kb):
    assert temp_kb.load_shared_ids() == set()

    temp_kb.add_shared_id("entry-123")
    temp_kb.add_shared_id("entry-456")

    shared = temp_kb.load_shared_ids()
    assert shared == {"entry-123", "entry-456"}

def test_find_pending_pollinate_only_manual_and_unshared(temp_kb):
    # 添加不同类型的记录
    temp_kb.add_to_kb(task="系统生成任务", branch_a="", branch_b="", synthesis="系统方案",
                      model_id="deepseek-v4-flash", user_id="user_1")
    temp_kb.add_to_kb(task="手动授粉任务", branch_a="", branch_b="", synthesis="手动方案",
                      model_id="manual_pollinate", user_id="user_1")
    temp_kb.add_to_kb(task="已分享手动任务", branch_a="", branch_b="", synthesis="已分享方案",
                      model_id="manual_pollinate", user_id="user_1")
    # 标记第三个为已分享
    third_id = temp_kb.load_kb()[-1]["id"]
    temp_kb.add_shared_id(third_id)

    pending = temp_kb.find_pending_pollinate("user_1")
    assert pending is not None
    assert pending["model_id"] == "manual_pollinate"
    assert pending["task"] == "手动授粉任务"

def test_find_pending_pollinate_no_record(temp_kb):
    assert temp_kb.find_pending_pollinate("user_1") is None

    temp_kb.add_to_kb(task="系统任务", branch_a="", branch_b="", synthesis="系统方案",
                      model_id="deepseek-v4-flash", user_id="user_1")
    assert temp_kb.find_pending_pollinate("user_1") is None

def test_tokenize_function(temp_kb):
    tokens = temp_kb.tokenize("Hello World, 你好世界")
    assert "hello" in tokens
    assert "world" in tokens
    assert "你好世界" in tokens
