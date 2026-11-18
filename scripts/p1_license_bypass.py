# -*- coding: utf-8 -*-
"""开发者环境：跳过本地 license 校验"""
F = "core/services/message/send.py"
c = open(F, encoding="utf-8").read()

# 在 403 raise 之前插入 bypass
OLD = '''                raise HTTPException(status_code=403, detail=f"授权未激活: {_lic_reason}")'''

NEW = '''                import os as _os_dev
                if _os_dev.path.exists("enable_free_mode.txt") or _os_dev.getenv("SASES_DEV_BYPASS_LICENSE") == "1":
                    print("[license] DEV BYPASS: 跳过本地 license 校验")
                else:
                    raise HTTPException(status_code=403, detail=f"授权未激活: {_lic_reason}")'''

if OLD not in c:
    print("[ERR] 锚点未找到，send.py 可能已改过")
    # 打印上下文
    i = c.find("授权未激活")
    if i > 0:
        print("上下文：")
        print(c[max(0,i-300):i+100])
else:
    c = c.replace(OLD, NEW, 1)
    open(F, "w", encoding="utf-8").write(c)
    print("[OK] send.py 已加 DEV BYPASS")
    print("[INFO] 重启服务后生效")
