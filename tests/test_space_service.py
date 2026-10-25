import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.space_service import SpaceService
import core.db as db
import core.space_service as space_module

@pytest.fixture
def temp_space(tmp_path, monkeypatch):
    """使用临时数据库，避免污染真实数据"""
    db_file = tmp_path / "test_users.db"
    monkeypatch.setattr(db, "DB_FILE", str(db_file))
    db.init_db()
    # 清空空间节点表，保证隔离
    with db.get_db() as conn:
        conn.execute("DELETE FROM space_nodes")
    return SpaceService()

def test_register_and_list_node(temp_space):
    temp_space.register_node("node-1", "Test Node", "A test harness node", capabilities=["test"])
    nodes = temp_space.list_nodes()
    assert len(nodes) >= 1  # 因为可能会自动注册自身节点，所以用 >=
    assert any(n["node_id"] == "node-1" for n in nodes)

def test_register_and_get_node(temp_space):
    temp_space.register_node("node-2", "Node 2", "Another node")
    node = temp_space.get_node("node-2")
    assert node is not None
    assert node["node_id"] == "node-2"

def test_update_reputation(temp_space):
    temp_space.register_node("node-3", "Node 3", "Node for reputation")
    temp_space.update_reputation("node-3", True)
    temp_space.update_reputation("node-3", False)
    node = temp_space.get_node("node-3")
    assert node["total_count"] == 2
    assert node["success_count"] == 1
    assert node["reputation"] == 0.75

def test_remote_invoke(temp_space):
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"success": True, "result": {"fahrenheit": 86.0}, "error": None}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, json, headers=None):
            return MockResponse()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(space_module.httpx, "Client", MockClient)

    temp_space.register_node("remote-node", "Remote Unit Converter", "Remote converter",
                             endpoint="http://fake-endpoint:8000")
    result = temp_space.invoke_remote_node("remote-node", {"celsius": 30})
    assert result["success"] is True
    assert result["result"]["fahrenheit"] == 86.0

def test_sync_from_peer(temp_space):
    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return [
                {"node_id": "peer-node-1", "name": "Peer Node 1", "description": "Peer", "node_type": "harness"},
                {"node_id": "peer-node-2", "name": "Peer Node 2", "description": "Peer", "node_type": "harness"}
            ]

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url, headers=None):
            return MockResponse()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(space_module.httpx, "Client", MockClient)

    result = temp_space.sync_from_peer("http://fake-peer:8001")
    assert result["success"] is True
    assert result["added"] == 2
    nodes = temp_space.list_nodes()
    assert any(n["node_id"] == "peer-node-1" for n in nodes)
    assert any(n["node_id"] == "peer-node-2" for n in nodes)
