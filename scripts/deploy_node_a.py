"""
Node-A 部署脚本：pull 代码 + 安装 systemd service + 重启
本地运行，通过 ssh 远程执行
"""
import subprocess, sys

SSH_BASE = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=no", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "ConnectTimeout=10"]
HOST = "root@47.96.87.147"

def run(cmd, timeout=120):
    full = SSH_BASE + [HOST, cmd]
    print(f"[deploy] {cmd[:80]}...")
    try:
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
        out = (r.stdout or "") + (r.stderr or "")
        print(out[-2000:])
        return r.returncode, out
    except subprocess.TimeoutExpired:
        print(f"[deploy] TIMEOUT after {timeout}s")
        return -1, "timeout"

steps = [
    ("git pull", "cd /root/sases && git pull origin main 2>&1"),
    ("cp service", "cp /root/sases/scripts/sases.service /etc/systemd/system/sases.service"),
    ("daemon-reload", "systemctl daemon-reload"),
    ("enable", "systemctl enable sases 2>&1"),
    ("restart", "systemctl restart sases"),
    ("wait", "sleep 5"),
    ("status", "systemctl is-active sases"),
    ("listen", "ss -tlnp | grep 8001 || echo 'NO_LISTEN'"),
    ("journal", "journalctl -u sases -n 15 --no-pager"),
]

for name, cmd in steps:
    rc, out = run(cmd)
    if name in ("status",) and "active" not in out:
        print(f"[deploy] FAILED at {name}")
        sys.exit(1)
    if name == "listen" and "NO_LISTEN" in out:
        print(f"[deploy] FAILED: 8001 not listening")
        sys.exit(1)

print("[deploy] SUCCESS")
sys.exit(0)
