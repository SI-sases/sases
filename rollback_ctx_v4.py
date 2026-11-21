import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, "_ctx_v4_bak_20261120_072151")
for f in ['core/services/unified_context.py', 'core/services/model_service.py', 'users.db']:
    src = os.path.join(BAK, f.replace('/', '__'))
    dst = os.path.join(ROOT, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[RB] " + f + " 已恢复")
if os.path.exists(os.path.join(ROOT, 'core/services/ctx_limits.py')):
    os.remove(os.path.join(ROOT, 'core/services/ctx_limits.py'))
    print("[RB] ctx_limits.py 已删除")
print("回滚完成，重启服务")
