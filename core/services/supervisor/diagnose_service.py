import json
import re
from ..swarm.llm_parser import _call_llm

DIAGNOSE_SYSTEM_PROMPT = """你是SASES的首席诊断专家。
你的职责是阅读错误日志，找出报错的根本原因，并输出一条可以被指挥官直接执行的 #4 修复指令。

【核心铁律】
0. 如果你看到日志中包含“故意制造”、“raise”等字眼，说明代码中被人为埋了雷。请直接开处方：`#4: 修改 对应文件，删除 raise 语句`。
0. 严禁去修复 file_patch 等内置工具！如果报错信息是 `new_content` 未定义，直接开处方：`#4 使用 run_python 读取文件并将 xxx 替换为 yyy`。\n0. 严禁去修复文件操作工具（如 file_patch）本身的 Bug！你的任务只是修复业务代码中的报错！
1. 你绝对不能自己修改代码，你只输出一条 #4 指令。
2. 你的指令必须极其精准，明确告诉指挥官去修改哪个文件。
3. 你必须直接给出需要替换的旧代码片段（old_snippet）和新代码片段（new_snippet），严禁让执行员自己去“全局搜索”！

【输出格式示例】
如果报错是：NameError: name 'module_id' is not defined (在 core/tool_gateway.py)
你的输出必须是：
#4: 修改 core/tool_gateway.py。找到 except 块中的语句 `return ToolInvokeResponse(module_id=module_id, success=False, error=f"请求失败，已进入重试队列: {str(e)}")`，将其中的 `module_id=module_id` 替换为 `module_id=f"ext_api_{api_id}"`。

请直接输出以 #4 开头的单行文本，不要包含任何其他解释！
"""

async def diagnose_and_fix(error_log: str) -> str:
    try:
        prompt = f"错误日志:\n{error_log}\n\n请给出修复指令。"
        raw = await _call_llm(prompt, DIAGNOSE_SYSTEM_PROMPT)
        if not raw: return ""
        
        match = re.search(r'#4:.*', raw)
        if not match: return ""
        
        fix_command = match.group().strip()
        print(f"[diagnose] 🩺 医生开出处方: {fix_command}")
        return fix_command
    except Exception as e:
        print(f"[diagnose_service] 异常: {e}")
        return ""
