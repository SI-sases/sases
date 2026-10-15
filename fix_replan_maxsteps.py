import os
import shutil
import ast
from datetime import datetime

FP = "core/services/swarm/commander.py"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"core__services__swarm__commander.py.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

old = "async def replan_failed_steps(task: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:"
new = "async def replan_failed_steps(task: Dict[str, Any], max_steps: int = None) -> Optional[List[Dict[str, Any]]]:"

if old in c:
    c = c.replace(old, new, 1)
    print("已加 max_steps 参数")
else:
    print("警告：未匹配")
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
print("完成！")