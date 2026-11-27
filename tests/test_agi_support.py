import sqlite3

from agi import support


def test_classify_and_human_boundary():
    assert support.classify("安装后打不开")["level"] == "L2"
    refund = support.classify("我要退款")
    assert refund["human_required"] is True
    assert refund["level"] == "L3"


def test_kb_and_draft():
    hits = support.search("安装后打不开")
    assert hits and hits[0]["source"] == "install.md"
    draft = support.draft_reply("安装后打不开")
    assert draft["sources"] == ["install.md"]
    refused = support.draft_reply("我要退款")
    assert refused["needs_human"] is True


def test_ticket_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "agi.db"))
    ticket = support.create_ticket(conn, "安装后打不开", customer="u1")
    assert ticket["owner"] == "local"
    assert support.list_open(conn)[0]["id"] == ticket["id"]
    assert support.resolve(conn, ticket["id"]) is True
    assert support.list_open(conn) == []
    conn.close()
