import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(ROOT, "_run_id_bak_20261121_011711", "commander.py")
dst = os.path.join(ROOT, "core/services/swarm/commander.py")
if os.path.exists(src):
    shutil.copy2(src, dst)
    print("[RB] commander.py 已恢复")
