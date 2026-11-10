# fix.py
p = 'core/services/swarm/executor_callback.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 强制将错误的导入路径修改为正确的上层目录
c = c.replace('from .diagnose_service import diagnose_and_fix', 'from ..supervisor.diagnose_service import diagnose_and_fix')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print("✅ 路径导入已修复！请重启后端！")
