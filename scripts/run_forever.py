# scripts/run_forever.py
import os
import sys
import json
import logging
import socket
import subprocess
import time
import urllib.request

if os.environ.get("SASES_ENABLE_LOCAL_EMBEDDING") != "1":
    os.environ["SASES_DISABLE_LOCAL_EMBEDDING"] = "1"
    os.environ.setdefault("EMBEDDING_MODE", "api")
    print("[wrapper] 本地 embedding 已禁用，走 API 模式", flush=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

print("[wrapper] root=" + ROOT, flush=True)
print("[wrapper] python=" + sys.executable, flush=True)
print("[wrapper] cwd=" + os.getcwd(), flush=True)

business_logger = logging.getLogger("business")
business_logger.setLevel(logging.INFO)
if not business_logger.handlers:
    fh = logging.FileHandler("sases.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    business_logger.addHandler(fh)
    business_logger.propagate = False

PORT = int(os.environ.get("SASES_PORT", "8001"))
HOST = os.environ.get("SASES_HOST", "0.0.0.0")
RESTART_SIGNAL = os.path.join(ROOT, "restart_signal.txt")
RUNTIME_PORT_FILE = os.path.join(ROOT, "runtime_port.json")


def _port_free(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _is_sases(port: int) -> bool:
    try:
        req = urllib.request.Request("http://127.0.0.1:%d/version" % port)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return "schema_version" in data or "node_id" in data
    except Exception:
        return False


def _write_runtime_port(port: int, requested: int) -> None:
    with open(RUNTIME_PORT_FILE, "w", encoding="utf-8") as handle:
        json.dump({"port": port, "requested_port": requested, "pid": os.getpid(),
                   "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, handle,
                  ensure_ascii=False, indent=2)


requested_port = PORT
if not _port_free(PORT):
    if _is_sases(PORT):
        print("[wrapper] SASES already running on %d, reuse it" % PORT, flush=True)
        _write_runtime_port(PORT, requested_port)
        sys.exit(0)
    for candidate in range(PORT + 1, PORT + 11):
        if _port_free(candidate):
            PORT = candidate
            print("[wrapper] port %d busy, fallback to %d" % (requested_port, PORT), flush=True)
            break
    else:
        print("[wrapper] no free port in fallback range", flush=True)
        sys.exit(1)

_write_runtime_port(PORT, requested_port)

if __name__ == "__main__":
    restart_count = 0
    while True:
        print("[wrapper] starting uvicorn on " + HOST + ":" + str(PORT) + " (restart#" + str(restart_count) + ")", flush=True)
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app_full:app", "--host", HOST, "--port", str(PORT), "--log-level", "info", "--no-access-log"],
                cwd=ROOT,
                env=os.environ.copy()
            )
            returncode = proc.wait()
        except KeyboardInterrupt:
            print("[wrapper] KeyboardInterrupt, terminating uvicorn", flush=True)
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            break

        if os.path.exists(RESTART_SIGNAL):
            try:
                os.remove(RESTART_SIGNAL)
                print("[wrapper] restart_signal detected and cleared, restarting", flush=True)
            except Exception as e:
                print("[wrapper] failed to clear restart_signal: " + str(e), flush=True)
        else:
            print("[wrapper] uvicorn exited with code " + str(returncode) + " (no restart_signal)", flush=True)

        if returncode == 0:
            restart_count += 1
            if restart_count > 50:
                print("[wrapper] too many restarts (50), giving up", flush=True)
                break
            time.sleep(1)
            continue
        else:
            print("[wrapper] nonzero exit code, stopping", flush=True)
            break
