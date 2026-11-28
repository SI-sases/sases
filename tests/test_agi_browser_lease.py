import threading
import time

from agi.browser_lease import BrowserLeases


def test_profile_leases_are_scoped():
    leases = BrowserLeases()
    entered = []

    def worker(name):
        with leases.acquire("default"):
            entered.append(name)

    with leases.acquire("default"):
        t = threading.Thread(target=worker, args=("blocked",))
        t.start()
        time.sleep(0.1)
        assert entered == []
    t.join(timeout=2)
    assert entered == ["blocked"]
    with leases.acquire("other"):
        assert True


def test_browser_profiles_mapping(monkeypatch):
    from agi import browser_profiles
    monkeypatch.setenv("SASES_BROWSER_PROFILES", '{"default":"http://a","account_a":"http://b"}')
    assert browser_profiles.cdp_for("default") == "http://a"
    assert browser_profiles.cdp_for("account_a") == "http://b"
