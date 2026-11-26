from core import credit_protocol


def test_protocol_is_canonical():
    assert credit_protocol.PROTOCOL == "sases-credit-v1"
    assert len(credit_protocol.RULES_HASH) == 64


def test_accepts_canonical_and_rejects_other():
    assert credit_protocol.accepted(credit_protocol.PROTOCOL)
    assert not credit_protocol.accepted("my-credit-v99")


def test_strict_requires_protocol(monkeypatch):
    monkeypatch.setenv("SASES_CREDIT_STRICT", "1")
    assert not credit_protocol.accepted(None)
