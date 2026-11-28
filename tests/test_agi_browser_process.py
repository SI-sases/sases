import subprocess
import sys

from agi import browser_process


def test_browser_process_kill():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    browser_process.register("agent-test", proc)
    assert browser_process.kill("agent-test") is True
    proc.wait(timeout=5)
    browser_process.unregister("agent-test", proc)
    assert proc.poll() is not None
