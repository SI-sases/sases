# -*- coding: utf-8 -*-
# 回滚脚本，自动生成于 20261120_065227
import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, "_ctx_bak_20261120_065227")
FILES = [
    "core/services/unified_context.py",
    "core/services/intent_service.py",
    "core/services/swarm/commander.py",
    "core/services/message/send.py",
    "core/services/swarm/prompts.py",
]
for f in FILES:
    src = os.path.join(BAK, f.replace("/", "__").replace("\\", "__"))
    dst = os.path.join(ROOT, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[RB] " + f + " 已恢复")
    elif f == "core/services/unified_context.py" and os.path.exists(dst):
        os.remove(dst)
        print("[RB] " + f + " 已删除（新建文件）")
    else:
        print("[RB] " + f + " 无备份")
print("回滚完成，请重启服务")
