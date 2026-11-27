import sqlite3
from pathlib import Path

from agi import context_builder, context_pack


def test_builder_redacts_and_dedupes(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    built = context_builder.build(
        conn, "publish",
        facts=[{"key": "password", "value": "secret"}],
        constraints=["dry-run", "dry-run"],
    )
    pack = context_pack.get(conn, built["context_id"])
    assert pack["facts"][0]["value"] == "[redacted]"
    assert pack["constraints"] == ["dry-run"]
    assert built["tokens"] > 0
    conn.close()


def test_builder_artifact_and_conversation_lookup(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    f = tmp_path / "a.mp4"
    f.write_bytes(b"0123456789")
    built = context_builder.build_from_paths(conn, "publish", [str(f)], conversation_id=42)
    assert built["artifacts"] == 1
    assert context_pack.find_by_conversation(conn, 42)["context_id"] == built["context_id"]
    conn.close()
