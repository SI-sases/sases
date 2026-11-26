from core.services import memory_service


def test_memory_roundtrip():
    item = memory_service.set_memory(1, "test_memory_key", "test_memory_value", "global")
    try:
        entries = memory_service.list_memory(1, "global")
        assert any(e["id"] == item["id"] for e in entries)
    finally:
        memory_service.delete_memory(1, item["id"])


def test_memory_requires_session_for_session_scope():
    try:
        memory_service.set_memory(1, "k", "v", "session")
    except ValueError:
        return
    raise AssertionError("session scope should require session_id")
