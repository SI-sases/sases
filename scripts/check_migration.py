import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

source = sys.argv[1]
fd, target = tempfile.mkstemp(suffix=".db")
os.close(fd)
src = sqlite3.connect(source)
dst = sqlite3.connect(target)
src.backup(dst)
dst.close()
src.close()

os.environ["SASES_DB_PATH"] = target
from core.db import init_db  # noqa: E402
from core.migrations import ensure_schema, current_version  # noqa: E402
from core.db import get_connection  # noqa: E402

init_db()
ensure_schema()
conn = get_connection()
print("schema", current_version(conn))
print("tables", conn.execute("select count(*) from sqlite_master where type='table'").fetchone()[0])
print("nodes", conn.execute("select count(*) from nodes").fetchone()[0])
conn.close()
os.remove(target)
