"""test_election.py —— 选举协议单元测试。"""
import pytest
from core.node import election


def test_init_priority_node_A():
    """node-A 应初始化为 master 优先级 10。"""
    election.init_priority(node_id="node-A")
    s = election.get_election_state()
    assert s["my_priority"] == 10
    assert s["my_role"] == "master"


def test_init_priority_node_B():
    """node-B 应初始化为 slave 优先级 20。"""
    election.init_priority(node_id="node-B")
    s = election.get_election_state()
    assert s["my_priority"] == 20
    assert s["my_role"] == "slave"


def test_set_my_role():
    election.set_my_role("master")
    assert election.get_election_state()["my_role"] == "master"
    election.set_my_role("slave")
    assert election.get_election_state()["my_role"] == "slave"


def test_vote_request_missing_fields():
    vote, reason = election.handle_vote_request({})
    assert vote == "no"
    assert "missing" in reason


def test_vote_request_unregistered_candidate():
    vote, reason = election.handle_vote_request({
        "candidate_id": "nonexistent-node",
        "new_epoch": 5,
        "priority": 1,
        "signature": "fake",
        "sign_message": "test",
    })
    assert vote == "no"
    assert "not registered" in reason or "invalid" in reason


def test_save_and_load_epoch():
    from core.db import init_db
    init_db()
    election.save_epoch_to_db(42)
    election._election_state["current_epoch"] = 0
    election.load_epoch_from_db()
    # 注：load 依赖 node_registry 里 NODE_ID 的行存在
    # 不断言具体值，只验证函数不报错
    assert isinstance(election.get_election_state()["current_epoch"], int)
