import os
import shutil
import ast
from datetime import datetime

FP = "core/services/intent_service.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__services__intent_service.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ===== 改动 1：_is_obvious_task 加宽 =====
old1 = '''    # 动词 + 名词组合
    for verb in TASK_VERBS:
        if verb in text:
            for noun in TASK_NOUNS:
                if noun in text:
                    return True
    return False'''

new1 = '''    # 操作动词（单字，覆盖更广）
    if re.search(r'(搜|查|找|看|读|写|改|跑|列|删|加|建|拿|抓|拉|发|传|算|数|比|统计|分析|整理|翻|捞|整|搞|弄)', text):
        return True
    # 动词 + 名词组合
    for verb in TASK_VERBS:
        if verb in text:
            for noun in TASK_NOUNS:
                if noun in text:
                    return True
    return False'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    changes += 1
    print("改动 1: _is_obvious_task 加操作动词")

# ===== 改动 2：_llm_judge 的 prompt =====
old2 = '''    prompt = f"""判断用户输入属于以下哪一类，只回答一个字母：

A) 普通聊天（问候、闲聊、情感表达、纯知识问答）
B) 可执行任务（需要操作计算机、抓取网页、查看文件、执行命令、调用工具等）

注意：包含 URL、文件路径、具体操作动词（抓取/下载/查看/列出）的输入，都判为 B。

用户输入：{content}

只回答 A 或 B。"""'''

new2 = '''    prompt = f"""判断用户输入属于以下哪一类，只回答一个字母：

A) 纯聊天（问候、寒暄、情感表达，不需要任何工具）
   例：你好、谢谢、今天心情不错、随便聊聊

B) 需要执行的任务（需要读文件/搜代码/执行命令/访问网络/调用工具）
   例：搜一下 X、读 Y 文件、看看 Z 目录、抓取这个网页、统计某字数

判断规则：
- 输入含"搜、查、找、读、改、跑、列、看、抓、下载、统计、分析"等操作词 → B
- 需要访问文件系统/网络/数据库才能回答 → B
- 只有纯粹的情感交流或闲聊 → A

用户输入：{content}

只回答 A 或 B。"""'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    changes += 1
    print("改动 2: _llm_judge prompt 优化")

# ===== 改动 3：is_task_intent 兜底加操作词判断 =====
old3 = '''    # 第二层：LLM 判断（中间地带）
    return await _llm_judge(content)'''

new3 = '''    # 第二层：LLM 判断（中间地带）
    llm_result = await _llm_judge(content)
    if not llm_result:
        # 兜底：LLM 判 chat，但内容含操作动词 → 仍判 task
        if re.search(r'(搜|查|找|看|读|写|改|跑|列|抓|下载|统计|分析)', content):
            return True
    return llm_result'''

if old3 in content:
    content = content.replace(old3, new3, 1)
    changes += 1
    print("改动 3: is_task_intent 兜底加操作词")

print(f"共完成 {changes} 处改动")

if changes == 0:
    print("警告：没有匹配到任何改动，可能文件已改过")
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