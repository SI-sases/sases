"""直达通道：单工具任务不走 swarm，直接调 harness 工具。

规则：
- 只用于"读"类工具（无副作用）
- 只处理"看起来简单"的请求（规则预筛 + LLM 判断）
- 执行结果直接写消息记录，不走 swarm 拆解
"""
import json
import re
import asyncio
import openai
from ... import config
from ...harness_runtime import harness_runtime

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
            return f"执行失败：{getattr(response, 'error', '未知错误')}"
        result = getattr(response, "result", None)
        if isinstance(result, dict):
            if result.get("success") is False:
                return f"执行失败：{result.get('error', '')}"
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
        return f"执行异常：{e}"


async def try_direct(content: str):
    """一站式入口：预筛 + 判断 + 执行。返回 (success: bool, result: str)"""
    if not _should_try_direct(content):
        return False, ""
    dec = await can_direct_execute(content)
    if not dec.get("direct"):
        return False, ""
    tool = dec["tool"]
    params = dec.get("params", {})
    print(f"[direct] 直达 {tool} params={params}")
    result = await execute_direct(tool, params)
    return True, result
