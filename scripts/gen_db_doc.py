"""扫描 users.db 生成 docs/DATABASE.md"""
import sqlite3
import os

DB = 'users.db'
OUT = 'docs/DATABASE.md'

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall() if not r[0].startswith('sqlite_')]

lines = ['# SASES 数据库结构\n', f'\n共 {len(tables)} 张表\n']
for t in tables:
    cur.execute(f'PRAGMA table_info({t})')
    cols = cur.fetchall()
    cur.execute(f'SELECT COUNT(*) FROM {t}')
    cnt = cur.fetchone()[0]
    lines.append(f'\n## {t} ({cnt} 行)\n')
    lines.append('| 字段 | 类型 | 默认 | 主键 |\n|------|------|------|------|\n')
    for c in cols:
        cid, name, ctype, notnull, dflt, pk = c
        lines.append(f'| {name} | {ctype} | {dflt or ""} | {"是" if pk else ""} |\n')

os.makedirs('docs', exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f'生成 {OUT}，共 {len(tables)} 张表')
conn.close()