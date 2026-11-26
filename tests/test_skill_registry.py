from core.services import skill_registry


def test_list_skills_contains_sases_control():
    names = {s["name"] for s in skill_registry.list_skills()}
    assert "sases-control" in names


def test_load_skill_rejects_traversal():
    try:
        skill_registry.load_skill("../SKILL")
    except KeyError:
        return
    raise AssertionError("traversal should be rejected")
