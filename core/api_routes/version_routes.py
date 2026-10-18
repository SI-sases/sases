from fastapi import APIRouter
import subprocess, os, sqlite3

router = APIRouter()


@router.get("/version")
def get_version():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.getcwd(), text=True
        ).strip()
    except Exception:
        commit = "unknown"
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=os.getcwd(), text=True
        ).strip()
    except Exception:
        branch = "unknown"
    db_path = os.environ.get("SASES_DB_PATH", "users.db")
    schema = "unknown"
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        schema = f"tables:{len(tables)}"
        conn.close()
    except Exception:
        pass
    return {
        "commit": commit,
        "branch": branch,
        "schema": schema,
        "node_id": os.environ.get("SASES_NODE_ID", "unknown"),
        "port": os.environ.get("SASES_PORT", "8001"),
    }
