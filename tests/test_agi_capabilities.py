from agi import capabilities
from agi.tools import build_default_registry


def test_role_policy_audit_is_clean():
    reg = build_default_registry()
    out = capabilities.check(reg)
    assert out["ok"] is True
    assert out["violations"] == []
    assert "deploy.promote" in out["control_plane"]
    assert "local.fs.read" in out["local_only"]
    assert reg.invoke("main", "capability.list", {})["ok"] is True
