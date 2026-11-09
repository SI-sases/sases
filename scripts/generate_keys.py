import os
import sys
import sqlite3
import random
import string
from datetime import datetime

# 绝对路径定位 users.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'users.db')

def generate_key():
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    return f"SASES-{parts[0]}-{parts[1]}-{parts[2]}"

def main():
    if len(sys.argv) != 4:
        print("用法: python scripts/generate_keys.py <数量> <类型> <天数>")
        print("示例: python scripts/generate_keys.py 10 month 30")
        sys.exit(1)

    count = int(sys.argv[1])
    key_type = sys.argv[2]
    days = int(sys.argv[3])

    if not os.path.exists(DB_PATH):
        print(f"❌ 找不到数据库文件: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    keys = []

    print(f"开始生成 {count} 张 {key_type} 卡密（有效期 {days} 天）...\n")
    
    for _ in range(count):
        k = generate_key()
        # 确保不重复
        while True:
            cur.execute("SELECT 1 FROM license_keys WHERE key_code=?", (k,))
            if not cur.fetchone():
                break
            k = generate_key()
            
        keys.append(k)
        cur.execute(
            "INSERT INTO license_keys (key_code, key_type, duration_days, status, created_at) VALUES (?, ?, ?, 'unused', ?)",
            (k, key_type, days, datetime.now().isoformat())
        )

    conn.commit()
    conn.close()

    print("✅ 卡密生成成功！请妥善保存：\n")
    for k in keys:
        print(k)
    print(f"\n共 {count} 张，已入库。")

if __name__ == '__main__':
    main()