import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, "_run_id_v2_bak_20261121_012859")
for f in ['core/services/message/send.py', 'core/services/swarm/commander.py']:
    src = os.path.join(BAK, f.replace('/', '__'))
    dst = os.path.join(ROOT, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[RB] " + f + " 已恢复")
print("回滚完成，重启服务")
