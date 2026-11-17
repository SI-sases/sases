# scripts/recon.py
import sqlite3, os, re

OUT = []
def w(s): OUT.append(s); print(s)

w("="*60); w("1. DB SCHEMA"); w("="*60)
conn = sqlite3.connect("users.db"); cur = conn.cursor()
for t in ["conversations","supervisor_runs","messages","swarm_pending_tasks","scheduled_tasks"]:
    w(f"\n[{t}]")
    try:
        cur.execute(f"PRAGMA table_info({t})")
        for r in cur.fetchall(): w(f"  {r[1]:30s} {r[2]}")
    except Exception as e: w(f"  ERR: {e}")

w("\n"+"="*60); w("2. KEY FILES"); w("="*60)
for f in ["core/services/task_state_service.py","core/services/intent_service.py",
          "core/services/message/send.py","core/services/context.py",
          "core/services/swarm/prompts.py","core/services/swarm/commander.py",
          "core/services/swarm/executor_callback.py","core/services/swarm/reviewer_deep.py",
          "core/services/supervisor/runs.py","core/services/supervisor/decider.py",
          "core/harness_runtime.py","core/bootstrap.py","core/db.py",
          "harness_modules/file_patch/main.py"]:
    ok = os.path.exists(f); sz = os.path.getsize(f) if ok else 0
    w(f"  {'Y' if ok else 'N'} {f} ({sz}B)")

w("\n"+"="*60); w("3. KEY FUNCTIONS (line)"); w("="*60)
def find(pat, fp, label):
    if not os.path.exists(fp): w(f"  N {label}: no file"); return
    for i, line in enumerate(open(fp, encoding="utf-8", errors="ignore"), 1):
        if re.search(pat, line): w(f"  L{i} {label}: {line.strip()[:90]}"); return
    w(f"  N {label}: not found")

find(r"def create_run", "core/services/supervisor/runs.py", "create_run")
find(r"def finish_run", "core/services/supervisor/runs.py", "finish_run")
find(r"def cancel_run", "core/services/supervisor/runs.py", "cancel_run")
find(r"handle_step_done", "core/services/swarm/executor_callback.py", "handle_step_done")
find(r"def classify", "core/services/intent_service.py", "classify")
find(r"def build_enriched_prompt", "core/services/context.py", "build_enriched_prompt")
find(r"def review_step", "core/services/swarm/reviewer_deep.py", "review_step")

w("\n"+"="*60); w("4. KEY RULES"); w("="*60)
def g(kw, fp, label):
    if not os.path.exists(fp): w(f"  N {label}"); return
    c = open(fp, encoding="utf-8", errors="ignore").read().count(kw)
    w(f"  {'Y' if c>0 else 'N'} {label}: {c}")

g("file_patch 已废弃", "core/services/swarm/prompts.py", "prompts:file_patch已废弃")
g("file_patch", "core/services/swarm/prompts.py", "prompts:file_patch总")
g("file_write", "core/services/swarm/prompts.py", "prompts:file_write")
g("file_read 返回值", "core/services/swarm/prompts.py", "prompts:file_read返回值")
g("DEPRECATED_TOOLS", "core/harness_runtime.py", "runtime:DEPRECATED_TOOLS")
g("_ensure_column", "core/db.py", "db:_ensure_column")

w("\n"+"="*60); w("5. INTENT SERVICE"); w("="*60)
if os.path.exists("core/services/intent_service.py"):
    c = open("core/services/intent_service.py", encoding="utf-8", errors="ignore").read()
    for k in ["CHAT_PATTERNS","TASK_VERBS","TASK_NOUNS","CONTINUE","RESUME","is_task"]:
        n = c.count(k)
        if n: w(f"  {k}: {n}")
    w(f"  return词: {set(re.findall(r'return\s+[\"'](\w+)[\"']', c))}")

w("\n"+"="*60); w("6. #4 分支"); w("="*60)
if os.path.exists("core/services/message/send.py"):
    for i, line in enumerate(open("core/services/message/send.py", encoding="utf-8", errors="ignore"), 1):
        if "_numbered_prefix_matched" in line or "#4" in line:
            w(f"  L{i}: {line.strip()[:100]}")

w("\n"+"="*60); w("7. file_patch 拦截位置"); w("="*60)
for f in ["harness_modules/file_patch/main.py","core/harness_runtime.py","core/services/executor_service.py"]:
    if os.path.exists(f):
        for i, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
            if "已废弃" in line or "DEPRECATED" in line:
                w(f"  {f}:L{i}: {line.strip()[:100]}")

w("\n"+"="*60); w("8. 最近3 runs"); w("="*60)
try:
    cur.execute("SELECT id,status,substr(goal,1,50),created_at FROM supervisor_runs ORDER BY id DESC LIMIT 3")
    for r in cur.fetchall(): w(f"  id={r[0]} st={r[1]} goal={r[2]} t={r[3]}")
except Exception as e: w(f"  ERR: {e}")

open("_recon_result.txt","w",encoding="utf-8").write("\n".join(OUT))
print("\n[OK] _recon_result.txt")
