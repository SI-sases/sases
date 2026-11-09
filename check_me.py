import sqlite3
c = sqlite3.connect('users.db').cursor()
# 看看现在的 id=2 到底是多少
c.execute('SELECT id, username, credits FROM users WHERE id=2')
print("数据库当前状态:", c.fetchall())

# 看看 api 怎么返回的
with open('core/api_routes/user_routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'credits' in line or 'seed' in line:
            print(f"{i+1} | {line.rstrip()}")