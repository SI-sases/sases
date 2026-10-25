import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "core", "services", "supervisor", "continuation.py")

with open(path, "r", encoding="utf-8") as f:
    code = f.read()

inject_code = """            try:
                with db_cursor(commit=True) as _c_credit:
                    _c_credit.execute("INSERT INTO messages (conversation_id, sender, content, msg_type) VALUES (?, 'assistant', '⚠️ 系统提示：您的积分不足或触发预算上限，任务已被迫终止。', 'standard')", (conversation_id,))
            except Exception:
                pass
            """

code = code.replace("finish_run(run_id, status='budget_exceeded')", inject_code + "finish_run(run_id, status='budget_exceeded')")
code = code.replace("finish_run(run_id, status='insufficient_credits')", inject_code + "finish_run(run_id, status='insufficient_credits')")

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Fixed: continuation.py 积分提示已强制插入！")
