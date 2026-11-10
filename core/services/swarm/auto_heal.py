from ..swarm.llm_parser import _call_llm
import re

AUTO_FIX_PROMPT = """你是SASES的底层故障修复器。
我会给你一段Python报错，请直接输出一行修复指令，格式必须为：
#4: 修改 <文件路径>，将 <旧代码> 替换为 <新代码>
严禁废话。"""

async def auto_heal_code(error_log: str) -> str:
    """拦截代码级错误，自动生成修复处方"""
    # 过滤：只诊断代码级崩溃，不诊断业务逻辑错误（省 Token）
    if not any(err in error_log for err in ("NameError", "TypeError", "SyntaxError", "AttributeError")):
        return ""
        
    # 截断：只取最后 800 字符（节省 Token）
    _short_log = error_log[-800:]
    try:
        raw = await _call_llm(f"报错日志：\n{_short_log}", AUTO_FIX_PROMPT)
        match = re.search(r'#4:.*', raw)
        if match:
            return match.group().strip()
    except Exception:
        pass
    return ""
