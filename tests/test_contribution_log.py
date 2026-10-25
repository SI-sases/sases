import os
import sys
import pytest

# 确保可以导入 core 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import contribution_log
from core import config

@pytest.fixture
def temp_log_db(tmp_path):
    """使用临时数据库文件，避免污染真实 users.db"""
    db_file = tmp_path / "test_users.db"
    # 保存原配置
    old_db = config.DB_FILE
    # 修改配置中的数据库路径
    config.DB_FILE = str(db_file)
    contribution_log.DB_FILE = str(db_file)
    contribution_log.init_log_table()
    yield contribution_log
    # 恢复原配置
    config.DB_FILE = old_db
    contribution_log.DB_FILE = old_db

def test_log_event_and_get_user_logs(temp_log_db):
    # 记录事件
    temp_log_db.log_event(user_id=1, event_type="seed_submit", target_id="seed-1", metadata={"description": "测试种子"})
    temp_log_db.log_event(user_id=1, event_type="manual_pollinate", target_id="kb-1", metadata={"reward": 3})

    logs = temp_log_db.get_user_logs(user_id=1)
    assert len(logs) == 2
    # 最近的在前面
    assert logs[0]["event_type"] == "manual_pollinate"
    assert logs[1]["event_type"] == "seed_submit"
    assert logs[0]["metadata"]["reward"] == 3
    assert logs[1]["target_id"] == "seed-1"

def test_get_all_logs(temp_log_db):
    temp_log_db.log_event(user_id=1, event_type="chat_retrieval", target_id="kb-1")
    temp_log_db.log_event(user_id=2, event_type="seed_submit", target_id="seed-2")

    all_logs = temp_log_db.get_all_logs(limit=10)
    assert len(all_logs) == 2
    # 按时间倒序，最后写入的在前
    assert all_logs[0]["user_id"] == 2
    assert all_logs[1]["user_id"] == 1

def test_count_logs(temp_log_db):
    assert temp_log_db.count_logs() == 0
    temp_log_db.log_event(user_id=1, event_type="seed_submit")
    temp_log_db.log_event(user_id=1, event_type="seed_submit")
    assert temp_log_db.count_logs() == 2

def test_empty_logs(temp_log_db):
    assert temp_log_db.get_user_logs(user_id=999) == []
    assert temp_log_db.get_all_logs(limit=10) == []
    assert temp_log_db.count_logs() == 0
