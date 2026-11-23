import pytest

from core import client_ops, db
from core.migrations import (
    _migrate_v13_node_identity,
    _migrate_v15_creator_review,
    _migrate_v16_creator_portfolio,
    _migrate_v17_client_ops,
    _migrate_v18_client_ops_lease,
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    path = tmp_path / "ops.db"
    monkeypatch.setattr(db, "DB_PATH", str(path))
    with db.db_cursor(commit=True) as cur:
        _migrate_v13_node_identity(cur)
        _migrate_v15_creator_review(cur)
        _migrate_v16_creator_portfolio(cur)
        _migrate_v17_client_ops(cur)
        _migrate_v18_client_ops_lease(cur)


def test_client_ops_claim_and_complete(temp_db):
    operation = client_ops.enqueue("node_test", "status", {"x": 1}, requested_by=3)
    claimed = client_ops.claim_next("node_test")
    assert claimed["id"] == operation["id"]
    assert claimed["status"] == "running"
    assert claimed["payload"] == {"x": 1}
    assert claimed["attempts"] == 1
    assert claimed["lease_until"]
    assert client_ops.complete(operation["id"], "done", {"ok": True})
    listed = client_ops.list_operations("node_test")
    assert listed[0]["status"] == "done"
    assert listed[0]["result"] == {"ok": True}


def test_client_ops_idempotency(temp_db):
    first = client_ops.enqueue("node_test", "status", {}, idempotency_key="same")
    second = client_ops.enqueue("node_test", "status", {}, idempotency_key="same")
    assert first["id"] == second["id"]


def test_client_ops_rejects_unknown_action(temp_db):
    with pytest.raises(client_ops.ClientOpsError):
        client_ops.enqueue("node_test", "rm -rf /")
