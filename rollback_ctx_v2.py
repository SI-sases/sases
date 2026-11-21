import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, "_ctx_v2_bak_20261120_070322")
f = "core/services/unified_context.py"
src = os.path.join(BAK, f.replace("/", "__"))
dst = os.path.join(ROOT, f)
if os.path.exists(src):
    shutil.copy2(src, dst)
    print("[RB] unified_context.py 已恢复")
print("回滚完成，重启服务")
