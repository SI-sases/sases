import asyncio
import json
import openai
from core import config

async def main():
    content = "读一下 core/config.py 前 10 行"
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
    print("=== 调用 LLM ===")
    client = openai.OpenAI(
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        timeout=30,
    )
    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=config.MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
    )
    msg = resp.choices[0].message
    print("\n=== content 字段 ===")
    print(repr(msg.content))
    print("\n=== reasoning_content 字段 ===")
    rc = getattr(msg, "reasoning_content", None)
    print(repr(rc))
    print("\n=== finish_reason ===")
    print(resp.choices[0].finish_reason)

asyncio.run(main())