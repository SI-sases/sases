from core.services import marketplace_service


def test_marketplace_has_entries():
    ids = {x["id"] for x in marketplace_service.list_entries()}
    assert {"sases-control", "example-tool", "read-readme"} <= ids


def test_marketplace_filter():
    items = marketplace_service.list_entries(kind="plugin")
    assert all(x["type"] == "plugin" for x in items)


def test_marketplace_unknown():
    try:
        marketplace_service.get_entry("missing")
    except KeyError:
        return
    raise AssertionError("missing entry should raise KeyError")
