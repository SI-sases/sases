import sqlite3
c = sqlite3.connect('users.db')
cur = c.cursor()

cur.execute("""
    UPDATE supervisor_runs SET status='failed'
    WHERE status NOT IN ('completed','cancelled','failed','rejected','interrupted','error','timeout','plan_failed')
""")
n1 = cur.rowcount

cur.execute("""
    UPDATE supervisor_runs SET status='failed'
    WHERE status IN ('running','running_resumed','restart_pending','proposed')
""")
n2 = cur.rowcount

cur.execute("""
    UPDATE swarm_pending_tasks SET status='cancelled'
    WHERE status NOT IN ('completed','cancelled','failed')
""")
n3 = cur.rowcount
c.commit()

print("清理历史态:", n1)
print("清理活跃态:", n2)
print("取消 task:", n3)

cur.execute("SELECT COUNT(*) FROM supervisor_runs WHERE status IN ('running','running_resumed','restart_pending','proposed')")
print("剩余活跃 run:", cur.fetchone()[0])
