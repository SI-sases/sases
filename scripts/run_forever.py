import subprocess, sys, time, os
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PORT = os.environ.get("SASES_PORT", "8001")

C = [sys.executable, "-m", "uvicorn", "app_full:app", "--port", _PORT]
BAD_ALLOC_THRESHOLD = 5

while True:
    signal = os.path.join(R, "restart_signal.txt")
    if os.path.exists(signal):
        try:
            os.remove(signal)
        except Exception:
            pass
        print("[wrapper] signal-restart", flush=True)
        time.sleep(2)
        continue

    # 端口上已有 SASES 在跑 → 退出，不重复启动
    try:
        import urllib.request
        urllib.request.urlopen(
            f'http://127.0.0.1:{_PORT}/hive/info', timeout=2
        ).close()
        print(f"[wrapper] port {_PORT} 已有 SASES 在跑，退出", flush=True)
        sys.exit(0)
    except Exception:
        pass

    print(f"[wrapper] start on :{_PORT}", flush=True)
    s = time.time()
    p = subprocess.Popen(
        C, cwd=R, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    rr = None
    bad_count = 0
    try:
        for l in p.stdout:
            print(l, end="", flush=True)
            if "bad allocation" in l:
                bad_count += 1
                print(f"[wrapper] bad alloc #{bad_count}", flush=True)
                if bad_count >= BAD_ALLOC_THRESHOLD:
                    rr = "bad alloc x5"
                    break
            if time.time() - s > 43200:
                rr = "max hours"
                break
    except KeyboardInterrupt:
        p.terminate()
        sys.exit(0)

    try:
        import subprocess as _sp
        _sp.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                capture_output=True, timeout=10)
    except Exception:
        try:
            p.terminate()
            p.wait(5)
        except Exception:
            p.kill()

    print("[wrapper] restart", rr, flush=True)
    time.sleep(5)
