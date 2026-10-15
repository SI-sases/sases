import os
import shutil
import ast
from datetime import datetime

FP = "core/services/feedback_service.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__services__feedback_service.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

# 修 _build_task_snapshot 的回退分支
old = '''    if not row:
        # 任务已完成：从 supervisor_runs.goal 拉目标
        with db_cursor() as cur:
            cur.execute(
                "SELECT goal FROM supervisor_runs WHERE id=(SELECT supervisor_run_id FROM swarm_reviews WHERE task_id=? LIMIT 1)",
                (task_id,)
            )
            r2 = cur.fetchone()
            _goal = r2["goal"] if r2 and r2["goal"] else ""
        return {
            "user_input": _goal[:2000],
            "mode": "swarm",
            "steps_total": 0,
            "steps_tools": [],
            "retry_count": 0,
            "has_answer": False,
            "context_hint": "",
        }'''

new = '''    if not row:
        # 任务已完成：从 conversations 最近的 user 消息取任务描述
        _input = ""
        try:
            with db_cursor() as cur:
                cur.execute(
                    "SELECT conversation_id FROM swarm_reviews WHERE task_id=? LIMIT 1",
                    (task_id,)
                )
                rev = cur.fetchone()
                if rev and rev["conversation_id"]:
                    cur.execute(
                        "SELECT content FROM messages WHERE conversation_id=? AND sender='user' ORDER BY id DESC LIMIT 1",
                        (rev["conversation_id"],)
                    )
                    m = cur.fetchone()
                    if m and m["content"]:
                        _input = str(m["content"])[:2000]
        except Exception as e:
            print(f"[feedback] 回退拉 user_input 失败: {e}")
        return {
            "user_input": _input,
            "mode": "swarm",
            "steps_total": 0,
            "steps_tools": [],
            "retry_count": 0,
            "has_answer": False,
            "context_hint": "",
        }'''

if old in c:
    c = c.replace(old, new, 1)
    print("改动: _build_task_snapshot 回退改从 messages 取")
else:
    print("警告：锚点未匹配")
    print("请检查 feedback_service.py 里 'swarm_reviews WHERE task_id' 附近")
    raise SystemExit(1)

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
print("2. 硬刷新浏览器")
print("3. 发 swarm 任务，完成后点 👎 → 应显示'已记录'")
print("4. del fix_feedback_snapshot.py")