import re

DIAGNOSE_SYSTEM_PROMPT = """你是系统诊断医生。
你必须输出且只输出一条以 `#4:` 开头的指令。指令的格式必须是：`#4: 修改 <文件名>，在 <函数/变量> 处，将 <旧代码> 替换为 <新代码>`。如果你无法确定具体的文件名和行号，请输出 `#4: 分析日志并修复错误`。
"""


async def diagnose_and_fix(raw: str) -> bool:
    if not raw:
        return False
    match = re.search(r'#4:.*', raw)
    if not match:
        return False
    instruction = match.group(0).strip()
    if not instruction.startswith('#4:'):
        return False
    return True
