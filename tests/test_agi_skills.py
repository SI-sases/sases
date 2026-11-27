from agi import skills


def test_skill_catalog_and_eval():
    catalog = skills.list_skills()
    assert any(s["name"] == "sases-control" for s in catalog)
    result = skills.evaluate_skill("sases-control")
    assert result["ok"] is True
    assert result["checks"]["has_version"] is True
