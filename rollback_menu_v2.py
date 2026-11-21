import os, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, "_menu_v2_bak_20261121_044637")
for f in ['static/modules/chat_menu.js', 'core/services/intent_service.py', 'core/api_routes/message_routes.py']:
    src = os.path.join(BAK, f.replace('/', '__'))
    dst = os.path.join(ROOT, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("[RB] " + f + " 已恢复")
print("回滚完成。前端 Ctrl+Shift+R，后端重启")
