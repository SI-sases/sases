import os
import re
import shutil
import ast
from datetime import datetime

backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

def _backup(fp):
    b = os.path.join(backup_dir, fp.replace("/", "__").replace("\\", "__") + f".{ts}.bak")
    shutil.copy2(fp, b)
    print(f"  备份: {b}")
    return b

def _check(c):
    try:
        ast.parse(c)
        return True
    except SyntaxError as e:
        print(f"  语法失败: {e}")
        return False

# ============ A 部分：prompt 规则前置 ============
print("\n[A] 修改 core/services/swarm/prompts.py")
FP_A = "core/services/swarm/prompts.py"
bA = _backup(FP_A)
with open(FP_A, 'r', encoding='utf-8') as f:
    cA = f.read()

m = re.search(r'COMMANDER_SYSTEM_PROMPT = """(.*?)"""', cA, re.DOTALL)
if not m:
    print("  找不到 COMMANDER_SYSTEM_PROMPT")
    raise SystemExit(1)

prompt = m.group(1)
ps, pe = m.start(1), m.end(1)
before_len = len(prompt)

# 提取【前提验证铁律】和【file_patch 硬规则】的完整内容
def extract_section(text, title):
    idx = text.find(title)
    if idx < 0:
        return None
    line_start = text.rfind('\n', 0, idx)
    line_start = 0 if line_start < 0 else line_start + 1
    next_idx = text.find('\n【', idx + len(title))
    if next_idx < 0:
        next_idx = len(text)
    return text[line_start:next_idx].rstrip()

p_pre = extract_section(prompt, '【前提验证铁律')
p_patch = extract_section(prompt, '【file_patch 硬规则')

if p_pre and p_patch:
    # 从原位删除
    prompt = prompt.replace(p_pre + '\n', '', 1)
    prompt = prompt.replace(p_patch + '\n', '', 1)
    # 插到【工作目录】段落之后
    idx_work = prompt.find('【工作目录】')
    if idx_work >= 0:
        next_idx = prompt.find('\n【', idx_work + 6)
        if next_idx < 0:
            next_idx = len(prompt)
        insert_block = '\n' + p_pre + '\n\n' + p_patch + '\n\n'
        prompt = prompt[:next_idx] + insert_block + prompt[next_idx:]
        print("  前提验证铁律 + file_patch 硬规则 移到最前面")
    else:
        print("  警告：找不到【工作目录】")
else:
    print(f"  警告：提取失败 pre={bool(p_pre)} patch={bool(p_patch)}")

# 删掉旧版【file_patch 三模式（v2.4.0）】
p_old = extract_section(prompt, '【file_patch 三模式')
if p_old:
    prompt = prompt.replace(p_old + '\n', '', 1)
    print(f"  删掉旧版【file_patch 三模式】(省 {len(p_old)} 字符)")

cA_new = cA[:ps] + prompt + cA[pe:]
if not _check(cA_new):
    shutil.copy2(bA, FP_A)
    raise SystemExit(1)
with open(FP_A, 'w', encoding='utf-8') as f:
    f.write(cA_new)
print(f"  {before_len} → {len(prompt)} 字符")

# ============ B 部分：position 归一化 ============
print("\n[B] 修改 harness_modules/file_patch/main.py")
FP_B = "harness_modules/file_patch/main.py"
bB = _backup(FP_B)
with open(FP_B, 'r', encoding='utf-8') as f:
    cB = f.read()

# 在 position 校验前插入归一化
old_pos = '''    if not anchor:
        raise ValueError("缺少 anchor_pattern 参数")
    if position not in ("before", "after", "replace_line"):
        raise ValueError(f"position 必须是 before/after/replace_line，收到: {position}")'''

new_pos = '''    if not anchor:
        raise ValueError("缺少 anchor_pattern 参数")
    # v2.6.0: position 归一化——容错 LLM 常见错误值
    _pos_aliases = {
        "replace": "replace_line",
        "replace_with": "replace_line",
        "overwrite": "replace_line",
        "insert": "after",
        "insert_after": "after",
        "append": "after",
        "insert_before": "before",
        "prepend": "before",
    }
    if isinstance(position, str):
        _orig_pos = position
        position = _pos_aliases.get(position.lower().strip(), position)
        if _orig_pos != position:
            print(f"[file_patch] position '{_orig_pos}' 归一化为 '{position}'")
    if position not in ("before", "after", "replace_line"):
        raise ValueError(f"position 必须是 before/after/replace_line，收到: {position}")'''

if old_pos in cB:
    cB = cB.replace(old_pos, new_pos, 1)
    print("  加 position 归一化")
else:
    print("  警告：position 校验锚点未匹配")
    raise SystemExit(1)

if not _check(cB):
    shutil.copy2(bB, FP_B)
    raise SystemExit(1)
with open(FP_B, 'w', encoding='utf-8') as f:
    f.write(cB)
print(f"  大小 {os.path.getsize(FP_B)} 字节")

print("\n完成！下一步：")
print("1. 重启服务：Ctrl+C 后 python scripts/run_forever.py")
print("2. 测 3 条任务（读/搜/改）")
print("3. 特别关注'改成 9000'这类数值修改任务是否能一次成功")
print("4. del fix_prompt_and_position.py")