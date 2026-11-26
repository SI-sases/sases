from core.services import workflow_registry, workflow_service


def test_workflow_discovered():
    ids = {w["id"] for w in workflow_registry.list_workflows()}
    assert "read-readme" in ids


def test_read_only_workflow_runs():
    r = workflow_service.run(1, "read-readme", {}, approve=False)
    assert r["status"] == "completed"
    assert r["results"][0]["ok"] is True


def test_substitution():
    assert workflow_service._sub({"x": "{{name}}"}, {"name": "ok"}) == {"x": "ok"}
