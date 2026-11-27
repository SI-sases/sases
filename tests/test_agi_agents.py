import sqlite3

import pytest

from agi import agents
from agi.executor import execute
from agi.package import TaskPackage
from agi.tools import ToolRegistry, ToolSpec


def test_agent_spawn_lease_and_finish(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    aid = agents.spawn(conn, "node-C", {"goal": "health"}, ttl=60,
                       name="health", goal="check health")
    assert agents.lease(conn, aid, "main", 60) is True
    assert agents.lease(conn, aid, "other", 60) is False
    assert agents.heartbeat(conn, aid, "main", 60) is True
    assert agents.finish(conn, aid, "done") is True
    assert agents.list_agents(conn, "done")[0]["agent_id"] == aid
    assert agents.get_agent(conn, aid)["name"] == "health"


def test_agent_messages_and_cancel(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    aid = agents.spawn(conn, "local", {"goal": "x"})
    agents.add_message(conn, aid, "parent_to_child", "steer", {"message": "go"})
    assert agents.messages(conn, aid)[0]["type"] == "steer"
    assert agents.cancel(conn, aid) is True
    assert agents.get_agent(conn, aid)["status"] == "cancelled"


def test_task_package_requires_acceptance():
    with pytest.raises(ValueError):
        TaskPackage(goal="x", node_id="node-C").validate()
    package = TaskPackage(goal="x", node_id="node-C", acceptance=["health ok"])
    assert package.to_dict()["trace_id"].startswith("trace_")


def test_tool_schema_rejects_missing_argument():
    reg = ToolRegistry()
    reg.register(ToolSpec(
        "x", lambda a: {"ok": True}, "read", frozenset({"main"}),
        input_schema={"type": "object", "required": ["url"], "properties": {"url": {"type": "string"}}},
    ))
    with pytest.raises(ValueError):
        reg.invoke("main", "x", {})
    assert reg.invoke("main", "x", {"url": "http://x"})["ok"] is True


def test_executor_runs_package_steps(tmp_path):
    reg = ToolRegistry()
    reg.register(ToolSpec("echo", lambda a: {"ok": True, "value": a.get("v")}, "read",
                          frozenset({"main", "sub"})))
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    package = TaskPackage(goal="echo", node_id="local", acceptance=["echo ok"],
                          steps=[{"tool": "echo", "args": {"v": 1}}],
                          tools_allowed=["echo"])
    result = execute(package, reg, conn, profile="sub")
    assert result["ok"] is True
    assert result["results"][0]["result"]["value"] == 1
    conn.close()


def test_agent_context_and_messages_ack(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    aid = agents.spawn(conn, "local", {"goal": "x"}, context={"conversation_id": 1},
                       model_profile="default", result_schema={"type": "object"},
                       parent_agent_id="parent", depth=1)
    agent = agents.get_agent(conn, aid)
    assert agent["context_json"] == '{"conversation_id": 1}'
    assert agent["depth"] == 1
    agents.add_message(conn, aid, "parent_to_child", "steer", {"message": "go"})
    msg = agents.unread_messages(conn, aid)[0]
    agents.ack_message(conn, msg["id"])
    assert agents.unread_messages(conn, aid) == []


def test_requeue_active_agent(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    conn.row_factory = sqlite3.Row
    aid = agents.spawn(conn, "local", {"goal": "x"}, status="active")
    assert agents.requeue(conn, aid) is True
    assert agents.get_agent(conn, aid)["status"] == "queued"
