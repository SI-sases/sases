import openai
import json
import re
import time
import os

from core import config
from core.db import get_db, init_db

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=30,
    max_retries=2
)

MODEL = config.MODEL_NAME

# 本地危险模式检测（快速预筛）
DANGEROUS_PATTERNS = [
    r'\bos\.system\s*\(',
    r'\bsubprocess\.(call|run|Popen)\s*\(',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bshutil\.rmtree\s*\(',
    r'\brm\s+-rf\b',
    r'\b__import__\s*\(',
    r'\bopen\s*\([^\)]*["\']w["\']\s*\)',
    r'\bsocket\.socket\s*\(',
]

def _local_quick_scan(text: str) -> bool:
    """本地快速预筛，返回 True 表示未发现危险模式"""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    return True

def scan_content(text):
    """原有的安全扫描函数，返回 (safe: bool, category: str)"""
    if _local_quick_scan(text):
        log_safety_scan(text, "safe")
        return True, "normal"

    prompt = f"""你是一个内容安全审核员。请判断以下内容是否安全。

内容：
{text[:2000]}

请只回复一个JSON对象，格式：
{{"safe": true, "category": "normal"}}
或
{{"safe": false, "category": "malicious"}}  // 恶意代码
{{"safe": false, "category": "high_risk"}}  // 高风险（如危险操作）

只回复JSON，不要其他文字。"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=50
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = json.loads(raw)
        safe = result.get("safe", True)
        category = result.get("category", "normal")
        return safe, category
    except Exception as e:
        log_safety_scan(text, "error", str(e))
        return False, "high_risk"

def log_safety_scan(content, category, detail=""):
    with get_db() as conn:
        conn.execute("""
        INSERT INTO safety_log (timestamp, content_preview, category, detail)
        VALUES (?, ?, ?, ?)
        """, (time.strftime("%Y-%m-%d %H:%M:%S"), content[:100], category, detail))

def before_add_to_kb(content):
    """入库前安全检查，返回是否允许入库"""
    safe, category = scan_content(content)
    if safe:
        log_safety_scan(content, "safe")
        return True
    else:
        log_safety_scan(content, category, "blocked")
        print(f"⚠️ 安全扫描拦截：{category}")
        return False

# ========== 新增：统一风险分级接口 ==========

def analyze_risk(text: str) -> dict:
    """
    统一风险分级接口，供所有合规检查调用。
    返回:
        {
            "level": "low" | "medium" | "high",
            "message": str  # 给用户的提示文案
        }
    """
    safe, category = scan_content(text)

    if safe:
        level = "low"
        message = ""
    else:
        if category == "malicious":
            level = "high"
            message = "检测到恶意代码，操作已被阻止。"
        elif category == "high_risk":
            level = "high"
            message = "检测到高风险操作，请确认来源是否可信。"
        else:
            # 未知风险类别，保守处理为 high
            level = "high"
            message = "检测到不安全内容，请谨慎操作。"

    return {"level": level, "message": message}
