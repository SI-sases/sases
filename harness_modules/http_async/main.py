# harness_modules/http_async/main.py
"""通用异步 HTTP：提交任务 -> 返回 handle -> poll 轮询状态。

只用标准库，避免给客户端增加依赖。
"""
import json
import time
import urllib.error
import urllib.request
from urllib.parse import quote

MAX_BODY = 256 * 1024
TIMEOUT = 15
_DEFAULT_DONE = ("done", "succeeded", "completed", "success", "finished")
_DEFAULT_FAIL = ("failed", "error", "cancelled", "canceled")


def _dig(obj, path, default=None):
    cur = obj
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            try:
                cur = cur[int(part)]
            except Exception:
                return default
        else:
            return default
    return cur if cur is not None else default


def _http(url, method="GET", body=None, headers=None):
    if not str(url).lower().startswith(("http://", "https://")):
        raise ValueError("只允许 http/https")
    req = urllib.request.Request(url, method=(method or "GET").upper())
    for k, v in (headers or {}).items():
        req.add_header(str(k), str(v))
    data = None
    if body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, data=data, timeout=TIMEOUT) as resp:
        raw = resp.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            raise ValueError("响应过大（>" + str(MAX_BODY) + " bytes）")
        text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def run(params):
    submit_url = params.get("submit_url")
    if not submit_url:
        return {"success": False, "error": "缺少 submit_url"}
    method = (params.get("submit_method") or "POST").upper()
    headers = params.get("headers") or {}
    body = params.get("submit_body")
    if body is None:
        body = {k: v for k, v in params.items() if k not in (
            "submit_url", "submit_method", "submit_body", "headers", "handle_path",
            "status_url", "state_path", "progress_path", "result_path", "done_values", "fail_values")}
    try:
        resp = _http(submit_url, method, body, headers)
    except Exception as e:
        return {"success": False, "error": "提交失败: " + str(e)}

    handle = _dig(resp, params.get("handle_path") or "task_id")
    if handle is None:
        handle = _dig(resp, "id") or _dig(resp, "handle") or _dig(resp, "task_id")
    if handle is None:
        return {"success": False, "error": "提交响应里找不到 handle: " + json.dumps(resp, ensure_ascii=False)[:300]}

    handle_payload = {
        "handle": str(handle),
        "submit_url": submit_url,
        "status_url": params.get("status_url") or "",
        "headers": headers,
        "state_path": params.get("state_path") or "status",
        "progress_path": params.get("progress_path") or "progress",
        "result_path": params.get("result_path") or "result",
        "done_values": params.get("done_values") or list(_DEFAULT_DONE),
        "fail_values": params.get("fail_values") or list(_DEFAULT_FAIL),
        "submitted_at": time.time(),
    }
    if not handle_payload["status_url"]:
        return {"success": False, "error": "缺少 status_url（需要包含 {handle}）"}
    return {"status": "submitted", "handle": json.dumps(handle_payload, ensure_ascii=False), "tool_id": "http_async"}


def poll(handle):
    try:
        hp = json.loads(handle) if isinstance(handle, str) else dict(handle)
    except Exception:
        return {"state": "failed", "error": "bad handle"}
    url = str(hp.get("status_url") or "").replace("{handle}", quote(str(hp.get("handle")), safe=""))
    try:
        resp = _http(url, "GET", None, hp.get("headers") or {})
    except Exception as e:
        return {"state": "failed", "error": "轮询失败: " + str(e)}
    state = str(_dig(resp, hp.get("state_path") or "status", "")).lower()
    progress = _dig(resp, hp.get("progress_path") or "progress", 0)
    try:
        progress = max(0, min(100, int(float(progress))))
    except Exception:
        progress = 0
    done = [str(x).lower() for x in (hp.get("done_values") or _DEFAULT_DONE)]
    fail = [str(x).lower() for x in (hp.get("fail_values") or _DEFAULT_FAIL)]
    if state in done:
        return {"state": "done", "result": _dig(resp, hp.get("result_path") or "result", resp)}
    if state in fail:
        return {"state": "failed", "error": str(_dig(resp, "error", state))}
    return {"state": "running", "progress": progress}
