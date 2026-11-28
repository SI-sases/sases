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
