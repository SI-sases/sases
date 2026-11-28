from agi.tools import build_default_registry


def test_skill_run_returns_instructions():
    out = build_default_registry().invoke("main", "skill.run", {"name": "sases-control"})
    assert out["ok"] is True
    assert out["mode"] == "instructions"
    assert out["body"]
