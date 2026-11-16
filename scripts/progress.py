import sqlite3, datetime, sys

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print(f"SASES 进度总览  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 70)

# 1. 活跃 run
cur.execute("""
    SELECT id, goal, status, current_round, credits_used, started_at
    FROM supervisor_runs
    WHERE status IN ('running','awaiting_async','pending')
    ORDER BY started_at DESC
""")
runs = cur.fetchall()
print(f"\n[活跃任务] {len(runs)} 个")
for r in runs:
    print(f"  run={r['id'][:12]}  round={r['current_round']}  credits={r['credits_used']}")
    print(f"    goal: {r['goal'][:80]}")
    print(f"    since: {r['started_at']}")

# 2. 最近完成
cur.execute("""
    SELECT id, goal, status, finished_at
    FROM supervisor_runs
    WHERE status IN ('completed','failed','timeout','loop_detected','budget_exceeded')
    ORDER BY finished_at DESC LIMIT 5
""")
print(f"\n[最近完成]")
for r in cur.fetchall():
    print(f"  {r['status']:<16} {r['finished_at'][:19]}  {r['goal'][:60]}")

# 3. 待处理
cur.execute("SELECT COUNT(*) c FROM swarm_pending_tasks WHERE status IN ('pending','running')")
print(f"\n[swarm 队列] {cur.fetchone()['c']} 个待处理")

# 4. 今日统计
today = datetime.date.today().isoformat()
cur.execute("""
    SELECT
      COUNT(*) total,
      SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) ok,
      SUM(CASE WHEN status IN ('failed','timeout','loop_detected') THEN 1 ELSE 0 END) bad
    FROM supervisor_runs WHERE started_at >= ?
""", (today,))
s = cur.fetchone()
if s['total']:
    print(f"\n[今日] 总 {s['total']}  成功 {s['ok']}  失败 {s['bad']}  成功率 {s['ok']/s['total']*100:.0f}%")

# 5. 最近失败原因
cur.execute("""
    SELECT id, goal, status FROM supervisor_runs
    WHERE status NOT IN ('completed','running','pending')
    ORDER BY finished_at DESC LIMIT 3
""")
print(f"\n[最近失败]")
for r in cur.fetchall():
    print(f"  {r['status']:<16} {r['goal'][:60]}")

print("=" * 70)
