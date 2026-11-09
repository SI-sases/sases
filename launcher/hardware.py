import subprocess
import hashlib
import uuid

def get_hardware_fingerprint():
    """获取设备唯一指纹（主板序列号 + MAC + C盘卷序列号）"""
    parts = []
    
    # 1. 主板序列号
    try:
        cmd = "wmic baseboard get serialnumber"
        out = subprocess.check_output(cmd, shell=True).decode('gbk', errors='ignore').split('\n')
        if len(out) > 1:
            parts.append(out[1].strip())
    except:
        pass
        
    # 2. MAC 地址 (UUID.getnode 会基于网卡 MAC 生成)
    try:
        parts.append(str(uuid.getnode()))
    except:
        pass
        
    # 3. C盘卷序列号
    try:
        cmd = "vol C:"
        out = subprocess.check_output(cmd, shell=True).decode('gbk', errors='ignore')
        # 简单提取一下卷序列号
        for line in out.split('\n'):
            if '序列号' in line or 'Serial' in line:
                parts.append(line.split()[-1].strip())
    except:
        pass

    raw_str = "|".join(parts) if parts else "fallback_device"
    # 用 SHA256 哈希，防止用户直接看明文
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()[:32]
