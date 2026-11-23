import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "scripts", "screen_agent.py")


def run(params):
    goal = str(params.get("goal") or "").strip()
    if not goal:
        raise ValueError("goal is required")
    cmd = [sys.executable, SCRIPT, "--goal", goal]
    if params.get("confirm"):
        cmd.append("--confirm")
    if params.get("verify"):
        cmd.append("--verify")
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-2000:],
        "confirmed": bool(params.get("confirm")),
    }
