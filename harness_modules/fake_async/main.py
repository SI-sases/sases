# harness_modules/fake_async/main.py
"""异步测试工具：run 返回 handle，poll 按时间推进。"""
import time


def run(params):
    seconds = max(1, int(params.get("seconds") or 10))
    handle = "fake_%d_%d" % (int(time.time()), seconds)
    return {"status": "submitted", "handle": handle, "seconds": seconds}


def poll(handle):
    try:
        _, start_s, seconds_s = str(handle).split("_")
        start = int(start_s)
        seconds = max(1, int(seconds_s))
    except Exception:
        return {"state": "failed", "error": "bad handle"}
    elapsed = max(0, time.time() - start)
    if elapsed >= seconds:
        return {"state": "done", "result": {"ok": True, "elapsed": int(elapsed), "fake": True}}
    return {"state": "running", "progress": int(elapsed / seconds * 100)}
