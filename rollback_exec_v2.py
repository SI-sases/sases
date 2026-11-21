import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, "_exec_v2_bak_20261121_045623")
for f in ['static/modules/chat_menu.js', 'static/modules/api.js', 'core/api_routes/message_routes.py']:
    src = os.path.join(BAK, f.replace('/', '__'))
    dst = os.path.join(ROOT, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[RB] " + f + " 已恢复")
print("回滚完成")
