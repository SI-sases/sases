from core.services import feedback_service as fb

TASK_ID = "t_1792072829253"
USER_ID = 2

print("=" * 60)
print("测试 1：提交首次反馈 👎")
print("=" * 60)
r = fb.submit_explicit(
    user_id=USER_ID,
    task_id=TASK_ID,
    rating="down",
    reason_tag="output_poor",
    reason_text="结果不够详细"
)
print(r)

print()
print("=" * 60)
print("测试 2：查询用户反馈历史")
print("=" * 60)
history = fb.get_user_feedback(USER_ID, limit=5)
for h in history:
    print(f"  [{h['rating']}] {h['task_id']} | {h['reason_tag']} | {h['task_summary'][:50]}")

print()
print("=" * 60)
print("测试 3：同一任务再提交 👍（测试追加不覆盖）")
print("=" * 60)
r2 = fb.submit_explicit(
    user_id=USER_ID,
    task_id=TASK_ID,
    rating="up",
    reason_text="其实还行"
)
print(r2)

print()
print("=" * 60)
print("测试 4：查询该任务所有反馈（应有 2 条，is_latest 分别）")
print("=" * 60)
by_task = fb.get_feedback_by_task(TASK_ID)
for f in by_task:
    print(f"  id={f['id']} rating={f['rating']} type={f['feedback_type']} text={f['reason_text']}")

print()
print("=" * 60)
print("测试 5：隐式反馈")
print("=" * 60)
r3 = fb.record_implicit(
    user_id=USER_ID,
    task_id=TASK_ID,
    rating="down",
    signal="user_cancelled"
)
print(r3)

print()
print("=" * 60)
print("测试 6：统计")
print("=" * 60)
stats = fb.get_stats(user_id=USER_ID, range_days=7)
print(stats)

print()
print("=" * 60)
print("测试 7：权限校验（用不存在的 user_id 反馈）")
print("=" * 60)
r4 = fb.submit_explicit(
    user_id=99999,
    task_id=TASK_ID,
    rating="up"
)
print(r4)