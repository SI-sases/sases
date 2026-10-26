import sqlite3, json
from collections import Counter

conn = sqlite3.connect('users.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print("SASES 知识库数据体检")
print("=" * 60)

# 1. swarm_reviews 总量与状态分布
print("\n【1】swarm_reviews（每步审核日志）")
cur.execute("SELECT COUNT(*) FROM swarm_reviews")
total = cur.fetchone()[0]
print(f"  总记录数: {total}")
cur.execute("SELECT exec_status, COUNT(*) as cnt FROM swarm_reviews GROUP BY exec_status ORDER BY cnt DESC")
for r in cur.fetchall():
    print(f"    {r['exec_status']}: {r['cnt']}")
cur.execute("SELECT review_result, COUNT(*) as cnt FROM swarm_reviews GROUP BY review_result")
print("  审核结果分布:")
for r in cur.fetchall():
    print(f"    {r['review_result']}: {r['cnt']}")

# 2. 失败命令重复率（预测可行性的核心指标）
print("\n【2】失败命令重复率（核心指标）")
cur.execute("""
    SELECT command, COUNT(*) as cnt 
    FROM swarm_reviews 
    WHERE exec_status IN ('failed', 'blocked') 
    GROUP BY command 
    ORDER BY cnt DESC 
    LIMIT 10
""")
rows = cur.fetchall()
if rows:
    print("  失败最多的命令 TOP 10:")
    for r in rows:
        cmd = (r['command'] or '')[:60]
        print(f"    [{r['cnt']}次] {cmd}")
else:
    print("  无失败记录")

cur.execute("""
    SELECT COUNT(DISTINCT command) as distinct_cmds, COUNT(*) as total_fails
    FROM swarm_reviews 
    WHERE exec_status IN ('failed', 'blocked')
""")
r = cur.fetchone()
if r and r['total_fails']:
    ratio = r['distinct_cmds'] / r['total_fails']
    print(f"  失败命令去重比: {r['distinct_cmds']}/{r['total_fails']} = {ratio:.2f}")
    print(f"  → 比值越低，重复失败越多，预测越有意义")

# 3. 失败原因类型分布
print("\n【3】失败原因类型分布")
cur.execute("""
    SELECT review_reason, COUNT(*) as cnt 
    FROM swarm_reviews 
    WHERE exec_status IN ('failed', 'blocked') AND review_reason IS NOT NULL
    GROUP BY review_reason 
    ORDER BY cnt DESC 
    LIMIT 15
""")
for r in cur.fetchall():
    reason = (r['review_reason'] or '')[:70]
    print(f"    [{r['cnt']}次] {reason}")

# 4. swarm_pending_tasks
print("\n【4】swarm_pending_tasks（任务级）")
cur.execute("SELECT COUNT(*) FROM swarm_pending_tasks")
print(f"  总任务数: {cur.fetchone()[0]}")
cur.execute("SELECT status, COUNT(*) as cnt FROM swarm_pending_tasks GROUP BY status")
for r in cur.fetchall():
    print(f"    {r['status']}: {r['cnt']}")

# 5. supervisor_runs
print("\n【5】supervisor_runs（自主运行）")
try:
    cur.execute("SELECT COUNT(*) FROM supervisor_runs")
    print(f"  总运行数: {cur.fetchone()[0]}")
    cur.execute("SELECT status, COUNT(*) as cnt FROM supervisor_runs GROUP BY status")
    for r in cur.fetchall():
        print(f"    {r['status']}: {r['cnt']}")
except Exception as e:
    print(f"  表不存在或查询失败: {e}")

# 6. safety_memory 按类型
print("\n【6】safety_memory（记忆库）")
cur.execute("SELECT COUNT(*) FROM safety_memory")
print(f"  总记忆数: {cur.fetchone()[0]}")
cur.execute("SELECT memory_type, COUNT(*) as cnt FROM safety_memory GROUP BY memory_type ORDER BY cnt DESC")
for r in cur.fetchall():
    print(f"    {r['memory_type']}: {r['cnt']}")

# 7. execution_notes
print("\n【7】execution_notes（执行笔记）")
try:
    cur.execute("SELECT COUNT(*) FROM execution_notes")
    print(f"  总数: {cur.fetchone()[0]}")
    cur.execute("SELECT outcome, COUNT(*) as cnt FROM execution_notes GROUP BY outcome")
    for r in cur.fetchall():
        print(f"    {r['outcome']}: {r['cnt']}")
except Exception as e:
    print(f"  表不存在: {e}")

# 8. interaction_patterns
print("\n【8】interaction_patterns（经验库）")
try:
    cur.execute("SELECT COUNT(*) FROM interaction_patterns")
    print(f"  总数: {cur.fetchone()[0]}")
    cur.execute("SELECT pattern_type, COUNT(*) as cnt FROM interaction_patterns GROUP BY pattern_type")
    for r in cur.fetchall():
        print(f"    {r['pattern_type']}: {r['cnt']}")
    cur.execute("SELECT domain, COUNT(*) as cnt FROM interaction_patterns GROUP BY domain")
    print("  按领域分布:")
    for r in cur.fetchall():
        print(f"    {r['domain']}: {r['cnt']}")
    # 高置信度 pattern
    cur.execute("SELECT COUNT(*) FROM interaction_patterns WHERE confidence > 0.7 AND hit_count > 5")
    print(f"  高置信高命中的 pattern: {cur.fetchone()[0]}")
except Exception as e:
    print(f"  表不存在: {e}")

# 9. failed_cases
print("\n【9】failed_cases（失败案例）")
try:
    cur.execute("SELECT COUNT(*) FROM failed_cases")
    print(f"  总数: {cur.fetchone()[0]}")
except Exception as e:
    print(f"  表不存在: {e}")

# 10. candidate_rules（如果已建）
print("\n【10】candidate_rules（候选规则）")
try:
    cur.execute("SELECT COUNT(*) FROM candidate_rules")
    print(f"  总数: {cur.fetchone()[0]}")
    cur.execute("SELECT status, COUNT(*) as cnt FROM candidate_rules GROUP BY status")
    for r in cur.fetchall():
        print(f"    {r['status']}: {r['cnt']}")
except Exception as e:
    print(f"  表不存在（正常，尚未建）")

# 11. 综合判断
print("\n" + "=" * 60)
print("综合判断")
print("=" * 60)

cur.execute("SELECT COUNT(*) FROM swarm_reviews WHERE exec_status IN ('failed','blocked')")
fail_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM swarm_reviews WHERE exec_status='success'")
succ_count = cur.fetchone()[0]

print(f"\n执行层: 成功 {succ_count} / 失败 {fail_count}")

# 预测可行性判断
cur.execute("""
    SELECT command, COUNT(*) as cnt FROM swarm_reviews
    WHERE exec_status IN ('failed','blocked')
    GROUP BY command
    ORDER BY cnt DESC
    LIMIT 10
""")
_top10_rows = cur.fetchall()
_top10_sum = sum(r[1] for r in _top10_rows)
_coverage = _top10_sum / max(fail_count, 1)
print(f"TOP 10 命令覆盖失败数: {_top10_sum} / {fail_count} = {_coverage*100:.1f}%")

if fail_count < 50:
    print("\n【结论】失败数据太少，先积累，不做预测")
elif _coverage >= 0.5:
    print("\n【结论】TOP 10 覆盖率高，失败高度集中，预测价值高")
elif _coverage >= 0.3:
    print("\n【结论】TOP 10 覆盖率中等，可做初步预测")
else:
    print("\n【结论】TOP 10 覆盖率低，失败分散，预测价值低")

conn.close()
