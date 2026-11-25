import sqlite3
import sys

c = sqlite3.connect(sys.argv[1])
row = c.execute("select sql from sqlite_master where type='table' and name='nodes'").fetchone()
print(row[0] if row else "no nodes table")
print([r[1] for r in c.execute("pragma table_info(nodes)")])
c.close()
