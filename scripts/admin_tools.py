import sqlite3
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'users.db')

def list_keys():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM license_keys")
    keys = cur.fetchall()
    print(f"{'卡密':<25} | {'状态':<8} | {'类型':<6} | {'绑定设备数'}")
    print("-" * 60)
    for k in keys:
        # 查这个卡密绑了几个设备
        cur.execute("SELECT COUNT(*) FROM device_bindings WHERE device_fingerprint IN (SELECT device_fingerprint FROM device_bindings)") # 简化版，实际应建立关联
        print(f"{k['key_code']:<25} | {k['status']:<8} | {k['key_type']:<6}")
    conn.close()

def ban_key(key_code):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE license_keys SET status='banned' WHERE key_code=?", (key_code,))
    if cur.rowcount > 0:
        print(f"✅ 卡密 {key_code} 已被停用（封禁）")
    else:
        print(f"❌ 未找到卡密 {key_code}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  查看所有卡密: python scripts/admin_tools.py list")
        print("  停用指定卡密: python scripts/admin_tools.py ban <key_code>")
    elif sys.argv[1] == "list":
        list_keys()
    elif sys.argv[1] == "ban" and len(sys.argv) == 3:
        ban_key(sys.argv[2])
    else:
        print("参数错误")