import os
import sqlite3

DB_FILE = 'schema_reference.db'
OUT_FILE = os.path.join('docs', 'schema_reference.txt')

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

os.environ['SASES_DB_PATH'] = DB_FILE

import core.db

core.db.init_db()
conn = sqlite3.connect(DB_FILE)
rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' OR type='index' ORDER BY name").fetchall()
conn.close()
lines = []
for name, sql in rows:
    lines.append('-- ' + str(name))
    lines.append(str(sql))
    lines.append('')
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(chr(10).join(lines))
table_count = sum(1 for n, s in rows if s and 'CREATE TABLE' in s)
print('lines', len(lines))
print('tables', table_count)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
