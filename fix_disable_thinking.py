import os
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

# ========== 1. 改 llm_parser.py ==========
print("\n[1/2] 修改 core/services/swarm/llm_parser.py")
FP1 = "core/services/swarm/llm_parser.py"
b1 = _backup(FP1)
with open(FP1, 'r', encoding='utf-8') as f:
    c1 = f.read()

old = '''    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=max_tokens
    )'''

new = '''    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=max_tokens,
        extra_body={"thinking": {"type": "disabled"}}
    )'''

if old in c1:
    c1 = c1.replace(old, new, 1)
    print("  + 加 extra_body thinking=disabled")
    if not _check(c1):
        shutil.copy2(b1, FP1)
        raise SystemExit(1)
    with open(FP1, 'w', encoding='utf-8') as f:
        f.write(c1)
    print(f"  已写入，大小 {os.path.getsize(FP1)} 字节")
else:
    print("  警告：锚点未匹配")
    raise SystemExit(1)

# ========== 2. 改 direct_channel.py（顺带优化） ==========
print("\n[2/2] 修改 core/services/message/direct_channel.py")
FP2 = "core/services/message/direct_channel.py"
b2 = _backup(FP2)
with open(FP2, 'r', encoding='utf-8') as f:
    c2 = f.read()

old2 = '''            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )'''

new2 = '''            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            extra_body={"thinking": {"type": "disabled"}},
        )'''

if old2 in c2:
    c2 = c2.replace(old2, new2, 1)
    print("  + 加 extra_body thinking=disabled")
    if not _check(c2):
        shutil.copy2(b2, FP2)
        raise SystemExit(1)
    with open(FP2, 'w', encoding='utf-8') as f:
        f.write(c2)
    print(f"  已写入，大小 {os.path.getsize(FP2)} 字节")
else:
    print("  警告：锚点未匹配（可能已改过），跳过")

print("\n完成！下一步：")
print("1. 重启服务：Ctrl+C 后 python scripts/run_forever.py")
print("2. 测试复杂任务：'把 core/config.py 的 SUMMARY_MAX_TOKENS 改成 3000'")
print("3. 期望：一次生成完 file_patch 步骤，不再截断")
print("4. 验证后删除本脚本：del fix_disable_thinking.py")