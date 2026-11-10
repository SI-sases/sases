# fix.py
p = 'core/services/supervisor/decider.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 强行替换报错的变量
c = c.replace("_goal_text = run.get('goal', '')", "_goal_text = task.get('goal', '')")

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)

print("✅ 物理替换完成！`run` 已经改成 `task` 了。")
