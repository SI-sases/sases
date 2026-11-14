import sqlite3
import random
import string
from datetime import datetime

def generate_keys():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    
    # 确保表存在
    cur.execute("""
        CREATE TABLE IF NOT EXISTS license_keys (
            key_code TEXT PRIMARY KEY,
            key_type TEXT,
            duration_days INTEGER,
            status TEXT DEFAULT 'unused',
            created_at TEXT
        )
    """)
    
    # 定义 6 种卡密类型
    types = [
        ("体验卡", "trial", 1),
        ("周卡", "week", 7),
        ("月卡", "month", 30),
        ("季卡", "quarter", 90),
        ("半年卡", "half", 180),
        ("年卡", "year", 365)
    ]
    
    now_str = datetime.now().strftime("%Y%m%d")
    print("🚀 开始生成生产级激活码 (自动包含天数):\n")
    
    for name, prefix, days in types:
        rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        key_code = f"SASES-{now_str}-{prefix.upper()}-{rand}"
        
        cur.execute("INSERT INTO license_keys (key_code, key_type, duration_days, status, created_at) VALUES (?, ?, ?, 'unused', ?)",
                    (key_code, name, days, datetime.now().isoformat()))
        print(f"[{name} - {days}天] {key_code}")
        
    conn.commit()
    conn.close()
    print("\n✅ 所有卡密已入库！可以在启动器里输入这些卡密测试激活。")

if __name__ == "__main__":
    generate_keys()