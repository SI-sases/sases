from core.services import plugin_registry


def test_example_plugin_is_discovered():
    names = {p["id"] for p in plugin_registry.list_plugins()}
    assert "example-tool" in names


def test_unknown_plugin_rejected():
    try:
        plugin_registry.set_enabled("missing-plugin", True)
    except KeyError:
        return
    raise AssertionError("missing plugin should raise KeyError")
