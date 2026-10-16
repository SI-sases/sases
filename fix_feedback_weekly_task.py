import os
import shutil
import ast
from datetime import datetime

FP = "core/bootstrap.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__bootstrap.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

changes = 0

# ============ 改动 1：加 periodic_feedback_weekly 函数 ============
old1 = """async def periodic_pattern_finalize():"""

new1 = '''async def periodic_feedback_weekly():
    """每 7 天生成一次反馈周报（v0.40.0）"""
    import subprocess
    import sys as _sys
    import os as _os
    await asyncio.sleep(600)  # 启动后 10 分钟首跑
    repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    script = _os.path.join(repo, "scripts", "feedback_weekly.py")
    out = _os.path.join(repo, "docs", "feedback_weekly.md")
    while True:
        try:
            if not _os.path.exists(script):
                print("[feedback-weekly] 脚本不存在，跳过")
            else:
                r = subprocess.run(
                    [_sys.executable, script, "7", "--out", out],
                    cwd=repo, capture_output=True,
                    encoding="utf-8", errors="replace", timeout=120
                )
                if r.returncode == 0:
                    print("[feedback-weekly] 周报已生成")
                else:
                    print(f"[feedback-weekly] 生成失败: {(r.stderr or '')[:200]}")
        except Exception as e:
            print(f"[feedback-weekly] 异常: {e}")
        await asyncio.sleep(7 * 24 * 3600)


async def periodic_pattern_finalize():'''

if old1 in c and 'periodic_feedback_weekly' not in c:
    c = c.replace(old1, new1, 1)
    changes += 1
    print("改动 1: 加 periodic_feedback_weekly 函数")
else:
    print("改动 1: 跳过（已存在或未匹配）")

# ============ 改动 2：注册到后台任务列表 ============
old2 = """    _background_tasks.append(asyncio.create_task(periodic_airdrop()))"""

new2 = """    _background_tasks.append(asyncio.create_task(periodic_airdrop()))
    # 【周级】
    _background_tasks.append(asyncio.create_task(periodic_feedback_weekly()))"""

if old2 in c and 'periodic_feedback_weekly()' not in c:
    c = c.replace(old2, new2, 1)
    changes += 1
    print("改动 2: 注册 periodic_feedback_weekly")
else:
    print("改动 2: 跳过（已存在或未匹配）")

print(f"\n共 {changes} 处改动")

try:
    ast.parse(c)
    print("语法检查通过")
except SyntaxError as e:
    print(f"语法失败: {e}")
    shutil.copy2(backup, FP)
    raise SystemExit(1)

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("1. 重启服务")
print("2. 启动后等 10 分钟，服务日志应出现：[feedback-weekly] 周报已生成")
print("3. 检查：type docs\\feedback_weekly.md")
print("4. del fix_feedback_weekly_task.py")