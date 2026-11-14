import os
import re

p = "core/services/license_service.py"
if os.path.exists(p):
    c = open(p, "r", encoding="utf-8").read()
    
    if "def check_offline_grace" not in c:
        logic = '''

def check_offline_grace():
    """断网宽限期检查：如果断网，允许基于最后一次在线时间继续使用最多 7 天"""
    import os
    import json
    from datetime import datetime, timedelta
    if not os.path.exists("license.json"):
        return False, "no_license"
    try:
        with open("license.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        # 检查是否记录了最后一次成功的心跳时间
        last_time_str = data.get("last_server_time")
        if not last_time_str:
            # 如果连最后一次在线时间都没有，说明是一直没连上过
            return False, "no_last_time"
            
        last_time = datetime.fromisoformat(last_time_str)
        # 如果距离最后一次联网不超过 7 天，允许放行
        if datetime.now() - last_time < timedelta(days=7):
            return True, "offline_grace_period"
        else:
            return False, "offline_expired"
    except Exception as e:
        return False, f"error:{e}"
'''
        c += logic
        open(p, "w", encoding="utf-8").write(c)
        print("✅ 离线宽限期模块已注入 license_service.py")
    else:
        print("✅ 离线宽限期已存在")
else:
    print("❌ 找不到 license_service.py")