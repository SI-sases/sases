import json
import uuid
import time
from typing import List, Dict, Any, Optional

from core.db import get_db

def add_external_seed(description: str, test_cases: list, user_id: str, source: str = "external_api") -> Dict[str, Any]:
    seed_id = str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute("""
        INSERT INTO external_seed_pool (id, description, test_cases, source, user_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (seed_id, description, json.dumps(test_cases), source, str(user_id), timestamp))
    return {
        "id": seed_id,
        "description": description,
        "test_cases": test_cases,
        "source": source,
        "user_id": str(user_id),
        "timestamp": timestamp
    }

def list_external_seeds() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM external_seed_pool").fetchall()
    return [_row_to_seed_dict(row) for row in rows]

def clear_external_seeds():
    with get_db() as conn:
        conn.execute("DELETE FROM external_seed_pool")

def delete_external_seed(seed_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM external_seed_pool WHERE id = ?", (seed_id,))

def add_main_seed(description: str, test_cases: list, user_id: str, source: str = "external_api") -> Dict[str, Any]:
    seed_id = str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute("""
        INSERT INTO main_seed_pool (id, description, test_cases, source, user_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (seed_id, description, json.dumps(test_cases), source, str(user_id), timestamp))
    return {
        "id": seed_id,
        "description": description,
        "test_cases": test_cases,
        "source": source,
        "user_id": str(user_id),
        "timestamp": timestamp
    }

def list_main_seeds() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM main_seed_pool").fetchall()
    return [_row_to_seed_dict(row) for row in rows]

def delete_main_seed(seed_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM main_seed_pool WHERE id = ?", (seed_id,))

def clear_main_seeds():
    with get_db() as conn:
        conn.execute("DELETE FROM main_seed_pool")

def _row_to_seed_dict(row) -> Dict[str, Any]:
    d = dict(row)
    if d.get("test_cases"):
        try:
            d["test_cases"] = json.loads(d["test_cases"])
        except:
            d["test_cases"] = []
    else:
        d["test_cases"] = []
    return d
