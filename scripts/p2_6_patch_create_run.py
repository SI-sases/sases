# scripts/p2_6_patch_create_run.py
import shutil
from datetime import datetime

TARGET = "core/services/supervisor/runs.py"

OLD_SIG = "def create_run(user_id, conversation_id, supervisor_id, goal, task_type=None, max_rounds: int = None):"
NEW_SIG = "def create_run(user_id, conversation_id, supervisor_id, goal, task_type=None, max_rounds: int = None, trigger_type: str = 'user', trigger_task_id: str = None):"

OLD_SQL = '''cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]', ?)", (user_id, conversation_id, supervisor_id, goal, _mr, _tt))'''

NEW_SQL = '''cur.execute("INSERT INTO supervisor_runs (user_id, conversation_id, supervisor_id, goal, status, current_round, max_rounds, history, task_type, trigger_type, trigger_task_id) VALUES (?, ?, ?, ?, 'running', 0, ?, '[]', ?, ?, ?)", (user_id, conversation_id, supervisor_id, goal, _mr, _tt, trigger_type, trigger_task_id))'''

def main():
    content = open(TARGET, "r", encoding="utf-8").read()

    if "trigger_type: str = 'user'" in content:
        print("already patched, skip")
        return

    if OLD_SIG not in content:
        print("ERROR: 函数签名不匹配，停下来确认")
        return

    if OLD_SQL not in content:
        print("ERROR: SQL 语句不匹配，停下来确认")
        print("实际内容片段:")
        idx = content.find("INSERT INTO supervisor_runs")
        print(content[idx-50:idx+300])
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, TARGET + ".bak_p2_6_" + ts)
    print("backup done")

    new_content = content.replace(OLD_SIG, NEW_SIG, 1)
    new_content = new_content.replace(OLD_SQL, NEW_SQL, 1)

    open(TARGET, "w", encoding="utf-8").write(new_content)
    print("patched: " + TARGET)

if __name__ == "__main__":
    main()