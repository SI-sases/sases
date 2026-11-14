import os, sys, json, base64, uuid
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization

# 将项目根目录加入 sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

def generate_license():
    # 1. 获取硬件指纹 (直接调用 launcher 模块)
    try:
        from launcher.hardware import get_hardware_fingerprint
        fp = get_hardware_fingerprint()
    except ImportError:
        # 如果还找不到，就用系统底层 MAC 地址模拟一个
        fp = str(uuid.getnode())
        print(f"⚠️ 无法加载 launcher 模块，使用模拟指纹: {fp}")
    
    # 2. 设置过期时间（1年后）
    expire_at = (datetime.now() + timedelta(days=365)).isoformat()
    
    # 3. 构造载荷
    user_id = 1 # 默认管理员账号
    msg = f"{user_id}|{fp}|{expire_at}".encode('utf-8')
    
    # 4. 读取私钥并签名
    priv_path = os.path.join(ROOT_DIR, "core", "keys", "license_priv.pem")
    with open(priv_path, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    
    sig = base64.b64encode(priv.sign(msg)).decode("utf-8")
    
    # 5. 写入 license.json
    data = {
        "user_id": user_id,
        "device_fp": fp,
        "expire_at": expire_at,
        "key_code": "LOCAL-TEST-UNLIMITED",
        "sig": sig
    }
    
    with open(os.path.join(ROOT_DIR, "license.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("✅ 测试版 license.json 已生成，有效期至:", expire_at)
    print("🎉 现在重启服务，发送 #4 指令应该能完美放行了！")

if __name__ == "__main__":
    generate_license()