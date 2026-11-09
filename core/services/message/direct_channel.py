"""直达通道：单工具任务不走 swarm，直接调 harness 工具。

规则：
- 只用于"读"类工具（无副作用）
- 只处理"看起来简单"的请求（规则预筛 + LLM 判断）
- 执行结果直接写消息记录，不走 swarm 拆解
"""
import json
import re
import asyncio
import os
import time
from datetime import datetime
import openai
from ... import config
from ...harness_runtime import harness_runtime

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LOG_DIR = os.path.join(_ROOT, "data")
LOG_FILE = os.path.join(LOG_DIR, "direct_channel.jsonl")
LOG_KEEP_DAYS = 30
_last_cleanup_date = None

DIRECT_TOOLS = {
    "file_read": "读文件内容",
    "dir_tree": "列目录树",
    "grep_code": "搜索代码",
    "web_fetch": "抓取网页",
}

_READ_KW = ("读", "看一下", "看看", "搜", "找", "列出", "显示", "抓取", "抓一下", "打印")
_WRITE_KW = ("改", "写", "创建", "删除", "加一个", "实现", "重写", "重构")
_FILE_PAT = re.compile(r"[\w/\-]+\.\w{1,6}")


def _should_try_direct(content: str) -> bool:
    """快速规则预筛：符合特征才尝试直达，避免每个任务都调 LLM。"""
    if not content:
        return False
    # 有明确写操作词 → 不直达
    if any(kw in content for kw in _WRITE_KW):
        return False
    # 有明确读操作词 → 尝试直达
    if any(kw in content for kw in _READ_KW):
        return True
    # 无操作词但有文件路径或"目录" → 尝试直达
    if _FILE_PAT.search(content) or "目录" in content:
        return True
    return False


_STRONG_PATTERNS = [
    # "读 X 最后 N 行"
    (re.compile(r'^(?:读|看一下|看看|显示|打印|打开)(?:一下|下)?\s+([\w/\-\.]+\.\w{1,6})\s*(?:的)?\s*最后\s*(\d+)\s*行$'), 'file_read_tail'),
    # "读 X 第 N 到 M 行"
    (re.compile(r'^(?:读|看一下|看看|显示|打印|打开)(?:一下|下)?\s+([\w/\-\.]+\.\w{1,6})\s*(?:的)?\s*第\s*(\d+)\s*[到至\-~]\s*(\d+)\s*行'), 'file_read_range'),
    # "读 X 第 N 行"
    (re.compile(r'^(?:读|看一下|看看|显示|打印|打开)(?:一下|下)?\s+([\w/\-\.]+\.\w{1,6})\s*(?:的)?\s*第\s*(\d+)\s*行'), 'file_read_line'),
    # "读一下 xxx.py" / "看看 xxx.py 前 10 行"
    (re.compile(r'^(?:读|看一下|看看|显示|打印|打开)(?:一下|下)?\s+([\w/\-\.]+\.\w{1,6})(?:\s*(?:的)?\s*前?\s*(\d+)\s*行)?'), 'file_read'),
    # "搜一下 X 里的 Y"（带 path 的搜索）
    (re.compile(r'^(?:搜|搜索|查找|找)(?:一下|下)?\s+([\w/\-\.]+\.\w{1,6})\s*里的\s*([^\s，。]{1,})(?:[，,]\s*(?:带|显示)?(?:前后)?\s*(\d+)\s*行(?:上下文)?)?$'), 'grep_code_in_file'),
    # "搜 X 目录下的 Y"
    (re.compile(r'^(?:搜|搜索|查找|找)(?:一下|下)?\s+([\w/\-\.]+)\s*目录[下的里中]{0,3}\s*([^\s，。]{1,})(?:[，,]\s*(?:带|显示)?(?:前后)?\s*(\d+)\s*行(?:上下文)?)?$'), 'grep_code_in_dir'),
    # "在 X 里找 Y" / "在 X 里搜 Y"
    (re.compile(r'^(?:在)\s+([\w/\-\.]+)\s*(?:里|中|下)\s*(?:搜|找|查|查找)(?:一下|下)?\s+([^\s，。]{1,})$'), 'grep_code_in_file'),
    # "搜一下 xxx"
    (re.compile(r'^(?:搜|搜索|查找|找)(?:一下|下)?\s+([^\s，。]{2,})(?:[，,]\s*(?:带|显示)?(?:前后)?\s*(\d+)\s*行(?:上下文)?)?$'), 'grep_code'),
    # "看看 xxx 目录" / "列出 xxx 目录"
    (re.compile(r'^(?:看看|列出|显示|查看|列一下)(?:一下|下)?\s+([\w/\-\.]*)\s*(?:目录|文件夹)'), 'dir_tree'),
    # "抓取 https://"
    (re.compile(r'^(?:抓取|抓一下|爬取|请求|访问)\s+(https?://\S+)'), 'web_fetch'),
]


def _strong_direct_match(content: str):
    """强判：命中的话直接走直达，不再问 LLM。返回 dict 或 None。"""
    text = content.strip()
    for pat, tool in _STRONG_PATTERNS:
        m = pat.match(text)
        if not m:
            continue
        try:
            if tool == 'file_read_tail':
                fp = m.group(1)
                n = int(m.group(2))
                if n > 500:
                    n = 500
                return {'direct': True, 'tool': 'file_read', 'params': {'file_path': fp, 'tail_lines': n}}
            elif tool == 'file_read_line':
                fp = m.group(1)
                ln = int(m.group(2))
                return {'direct': True, 'tool': 'file_read', 'params': {'file_path': fp, 'lines': [ln]}}
            elif tool == 'file_read_range':
                fp = m.group(1)
                n1 = int(m.group(2))
                n2 = int(m.group(3))
                if n1 > n2:
                    n1, n2 = n2, n1
                cnt = n2 - n1 + 1
                if cnt > 500:
                    cnt = 500
                return {'direct': True, 'tool': 'file_read', 'params': {'file_path': fp, 'offset': n1 - 1, 'max_lines': cnt}}
            elif tool == 'file_read':
                fp = m.group(1)
                params = {'file_path': fp}
                if len(m.groups()) >= 2 and m.group(2):
                    params['max_lines'] = int(m.group(2))
                return {'direct': True, 'tool': 'file_read', 'params': params}
            elif tool == 'grep_code_in_file':
                fpath = m.group(1).strip()
                pattern = m.group(2).strip()
                if len(pattern) < 1:
                    continue
                params = {'pattern': pattern, 'path': fpath}
                if len(m.groups()) >= 3 and m.group(3):
                    try:
                        ctx = int(m.group(3))
                        if 1 <= ctx <= 10:
                            params['context_lines'] = ctx
                    except Exception:
                        pass
                return {'direct': True, 'tool': 'grep_code', 'params': params}
            elif tool == 'grep_code_in_dir':
                dpath = m.group(1).strip()
                pattern = m.group(2).strip()
                if len(pattern) < 1:
                    continue
                params = {'pattern': pattern, 'path': dpath}
                if len(m.groups()) >= 3 and m.group(3):
                    try:
                        ctx = int(m.group(3))
                        if 1 <= ctx <= 10:
                            params['context_lines'] = ctx
                    except Exception:
                        pass
                return {'direct': True, 'tool': 'grep_code', 'params': params}
            elif tool == 'grep_code':
                pattern = m.group(1).strip()
                if len(pattern) < 1:
                    continue
                params = {'pattern': pattern}
                if len(m.groups()) >= 2 and m.group(2):
                    try:
                        ctx = int(m.group(2))
                        if 1 <= ctx <= 10:
                            params['context_lines'] = ctx
                    except Exception:
                        pass
                return {'direct': True, 'tool': 'grep_code', 'params': params}
            elif tool == 'dir_tree':
                path = m.group(1).strip() or '.'
                return {'direct': True, 'tool': 'dir_tree', 'params': {'path': path}}
            elif tool == 'web_fetch':
                url = m.group(1).strip()
                return {'direct': True, 'tool': 'web_fetch', 'params': {'url': url}}
        except Exception:
            continue
    return None


async def can_direct_execute(content: str) -> dict:
    """判断能否直达。返回 {"direct": True, "tool": ..., "params": {...}} 或 {"direct": False}"""
    prompt = (
        "用户输入：" + content + "\n\n"
        "判断该请求是否可以用单个工具直接完成，不需要拆解步骤、不需要修改文件。\n\n"
        "可用工具：\n"
        "- file_read: 读文件内容。参数：file_path(必填), lines(行号数组，可选), grep(正则，可选), max_lines(默认300), offset(可选)\n"
        "- dir_tree: 列目录树。参数：path(默认.), max_depth(默认2)\n"
        "- grep_code: 搜索代码。参数：pattern(必填), path(可选), file_ext(可选), max_results(默认50)\n"
        "- web_fetch: 抓取网页文本。参数：url(必填)\n\n"
        "可以直达的例子：\n"
        '- "读一下 core/config.py" → file_read\n'
        '- "core/config.py 第 20 行" → file_read + lines\n'
        '- "core 目录下有哪些文件" → dir_tree\n'
        '- "搜一下 output_preview" → grep_code\n'
        '- "抓取 https://xxx 的内容" → web_fetch\n\n'
        "不可以直达的例子：\n"
        '- "改 config.py"（要改文件）\n'
        '- "创建新工具"（要拆解）\n'
        '- "统计所有 py 文件有多少个类"（要处理）\n\n'
        "如果可以用单个工具直接完成，输出 JSON（不要有其他文字）：\n"
        '{"direct": true, "tool": "工具名", "params": {...}}\n\n'
        "否则输出：\n"
        '{"direct": false}\n'
    )
    try:
        client = openai.OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            timeout=15,
        )
        resp = await asyncio.to_thread(
            client.chat.completions.create,
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            extra_body={"thinking": {"type": "disabled"}},
        )
        raw = (resp.choices[0].message.content or "").strip()
        i = raw.find("{")
        j = raw.rfind("}")
        if i >= 0 and j > i:
            dec = json.loads(raw[i:j + 1])
            if dec.get("direct") and dec.get("tool") in DIRECT_TOOLS:
                return dec
    except Exception as e:
        print(f"[direct] 判断失败: {e}")
    return {"direct": False}


async def execute_direct(tool: str, params: dict) -> str:
    """执行单个工具并返回结果文本。"""
    try:
        response = await asyncio.to_thread(harness_runtime.invoke_tool, tool, params)
        if not getattr(response, "success", False):
            _err = getattr(response, 'error', '未知错误')
            print(f"[direct] {tool} 失败: {_err}")
            _cands = getattr(response, 'result', None)
            if isinstance(_cands, dict) and _cands.get('candidates'):
                print(f"[direct] 候选: {_cands['candidates']}")
            return f"执行失败：{_err}"
        result = getattr(response, "result", None)
        if isinstance(result, dict):
            if result.get("success") is False:
                _err = result.get('error', '')
                print(f"[direct] {tool} 内层失败: {_err}")
                if result.get('candidates'):
                    print(f"[direct] 候选: {result['candidates']}")
                return f"执行失败：{_err}"
            if tool == "file_read":
                return result.get("content", "")
            elif tool == "dir_tree":
                return result.get("tree", "")
            elif tool == "grep_code":
                matches = result.get("matches", [])
                if not matches:
                    return "无匹配结果"
                lines = []
                for m in matches:
                    lines.append(f"{m.get('file', '?')}:{m.get('line', '?')}: {m.get('text', '')}")
                return "\n".join(lines)
            elif tool == "web_fetch":
                return result.get("text") or result.get("content") or str(result)
            return str(result)
        return str(result)
    except Exception as e:
        print(f"[direct] {tool} 异常: {e}")
        return f"执行异常：{e}"


def _log_direct(entry: dict):
    """写一行 JSONL 日志。每天最多清理一次旧日志。"""
    global _last_cleanup_date
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[direct] 写日志失败: {e}")
        return
    _today = datetime.now().strftime("%Y-%m-%d")
    if _last_cleanup_date != _today:
        _last_cleanup_date = _today
        try:
            _cleanup_old_inner(LOG_KEEP_DAYS)
        except Exception as e:
            print(f"[direct] 清理旧日志失败: {e}")


def _cleanup_old_inner(days: int):
    """保留最近 days 天的日志，其他删除。"""
    if not os.path.exists(LOG_FILE):
        return
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    kept = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("ts", "") >= cutoff:
                    kept.append(line)
            except Exception:
                continue
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")


async def try_direct(content: str, user_id=None, conversation_id=None):
    """一站式入口：预筛 + 判断 + 执行。返回 (success: bool, result: str)"""
    if not _should_try_direct(content):
        return False, ""
    # 先强判（不走 LLM）
    dec = _strong_direct_match(content)
    if dec:
        print(f"[direct] 强判命中 {dec['tool']}")
    else:
        # 走 LLM 判断
        dec = await can_direct_execute(content)
    if not dec.get("direct"):
        return False, ""
    tool = dec["tool"]
    params = dec.get("params", {})
    print(f"[direct] 直达 {tool} params={params}")
    _start = time.time()
    result = await execute_direct(tool, params)
    _dur = int((time.time() - _start) * 1000)
    _ok = not result.startswith("执行失败") and not result.startswith("执行异常")
    _log_direct({
        "ts": datetime.now().isoformat(),
        "user_id": user_id,
        "conv_id": conversation_id,
        "input": content[:200],
        "tool": tool,
        "params": params,
        "status": "success" if _ok else "failed",
        "result_len": len(result),
        "duration_ms": _dur,
    })
    return True, result
