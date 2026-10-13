import os
import shutil
import ast
from datetime import datetime

FP = "core/services/swarm/summarizer.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__services__swarm__summarizer.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    prompt = f"【背景】用户请求：{user_text}\\n\\n【执行过程】\\n{result_text}\\n\\n【要求】请直接输出最终结果，用于展示给用户。\\n- 绝对不要重复用户请求的内容。\\n- 如果工具返回了具体内容（文件内容、数据、答案），直接原样呈现。\\n- 如果任务只是完成某个操作（如改代码、发消息），用一句话说明完成情况。\\n- 直接输出结果本身，不要任何前缀、标题、格式说明。"'''

new = '''    prompt = f"""【背景】用户请求：{user_text}

【执行过程】
{result_text}

【强制规则（必须遵守）】
1. 如果工具返回了列表/多条匹配，必须**逐条完整列出**，禁止只说"部分结果"、"其余省略"、"前 N 条"。
2. 如果工具返回了文件内容，必须**完整输出**，不要总结成一句话。
3. **禁止**输出"已被截断"、"部分结果"、"其余在工具返回中"、"未完整显示"这类表达——数据库里数据是完整的，你没有理由省略。
4. 如果任务只是完成某个操作（如改代码、发消息），用一句话说明完成情况。
5. 绝对不要重复用户请求的内容。
6. 直接输出结果本身，不要任何前缀、标题、格式说明。

【输出】按以上规则直接输出最终结果。"""'''

if old in content:
    content = content.replace(old, new, 1)
    print("改动: prompt 加强制规则")
else:
    print("警告：没匹配到原 prompt，可能格式有差异")
    print("请把 summarizer.py 里 prompt = 那一段单独贴出来")
    raise SystemExit(1)

# 语法检查
try:
    ast.parse(content)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法检查失败: {e}")
    print("回滚...")
    shutil.copy2(backup, FP)
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"已写入 {FP}")
print(f"新文件大小: {os.path.getsize(FP)} 字节")