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


def test_fallback_policy_opt_in(monkeypatch):
    from agi import fallback_policy
    monkeypatch.delenv("SASES_AUTO_PROFILE_FALLBACK", raising=False)
    assert fallback_policy.enabled() is False
    assert fallback_policy.choose_profile("default", ["default", "account_a"]) == "account_a"


def test_platform_fallback_policy(monkeypatch):
    from agi import fallback_policy
    monkeypatch.delenv("SASES_AUTO_PLATFORM_FALLBACK", raising=False)
    assert fallback_policy.platform_enabled() is False
    assert fallback_policy.choose_platform("youtube", "video") == "bilibili"
    assert fallback_policy.choose_platform("douyin", "image") == ""
