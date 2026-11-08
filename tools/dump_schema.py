import sqlite3, sys
db_path = sys.argv[1]
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
for table in tables:
    print(f"TABLE {table}")
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        print(f"  COL {row[1]}|{row[2]}|NOTNULL={row[3]}|DEFAULT={row[4]}|PK={row[5]}")
    cur.execute(f"PRAGMA index_list({table})")
    for idx in cur.fetchall():
        print(f"  INDEX {idx[1]}|UNIQUE={idx[2]}")
        cur.execute(f"PRAGMA index_info({idx[1]})")
        for info in cur.fetchall():
            print(f"    IDX_COL {info[2]}")
