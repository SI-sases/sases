import json
import time
from typing import Dict, Any, List, Optional

from core.db import get_db, init_db
from core import config

class NodeRegistry:
    """节点注册与持久化（SQLite）"""

    def __init__(self):
        init_db()
        self._register_self()

    def _register_self(self):
        if config.NODE_ID and config.NODE_NAME:
            self.register_node(
                node_id=config.NODE_ID,
                name=config.NODE_NAME,
                description="SASES Node",
                node_type="sases_service",
                capabilities=["node_service"],
                endpoint=None,
                owner_id="self"
            )

    def _row_to_dict(self, row) -> dict:
        if not row:
            return None
        d = dict(row)
        if d.get("capabilities"):
            try:
                d["capabilities"] = json.loads(d["capabilities"])
            except:
                d["capabilities"] = []
        else:
            d["capabilities"] = []
        return d

    def register_node(self, node_id: str, name: str, description: str,
                      node_type: str = "harness", capabilities: List[str] = None,
                      endpoint: str = None, icon: str = None, owner_id: str = "system") -> Dict[str, Any]:
        capabilities = capabilities or []
        caps_json = json.dumps(capabilities)
        with get_db() as conn:
            existing = conn.execute("SELECT * FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
            if existing:
                conn.execute("""
                UPDATE space_nodes
                SET name = ?, description = ?, node_type = ?, capabilities = ?, endpoint = ?, icon = ?, owner_id = ?, registered_at = ?
                WHERE node_id = ?
                """, (name, description, node_type, caps_json, endpoint, icon, owner_id, time.strftime("%Y-%m-%d %H:%M:%S"), node_id))
            else:
                conn.execute("""
                INSERT INTO space_nodes (node_id, name, description, node_type, capabilities, endpoint, icon, owner_id, registered_at, reputation, success_count, total_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, 0, 0, 'unknown')
                """, (node_id, name, description, node_type, caps_json, endpoint, icon, owner_id, time.strftime("%Y-%m-%d %H:%M:%S")))
            row = conn.execute("SELECT * FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
        return self._row_to_dict(row)

    def list_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            if node_type:
                rows = conn.execute("SELECT * FROM space_nodes WHERE node_type = ?", (node_type,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM space_nodes").fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
        return self._row_to_dict(row)

    def update_reputation(self, node_id: str, success: bool):
        with get_db() as conn:
            node = conn.execute("SELECT total_count, success_count FROM space_nodes WHERE node_id = ?", (node_id,)).fetchone()
            if not node:
                return
            total = node["total_count"] + 1
            success_count = node["success_count"] + (1 if success else 0)
            reputation = 0.5 + (success_count / total) * 0.5 if total > 0 else 1.0
            conn.execute("""
            UPDATE space_nodes
            SET total_count = ?, success_count = ?, reputation = ?
            WHERE node_id = ?
            """, (total, success_count, reputation, node_id))

    def update_node_status(self, node_id: str, status: str):
        with get_db() as conn:
            conn.execute("UPDATE space_nodes SET status = ? WHERE node_id = ?", (status, node_id))

    def is_valid_node(self, node: dict) -> bool:
        required_fields = ["node_id", "name", "node_type"]
        for field in required_fields:
            if field not in node or not node[field]:
                return False
        if "capabilities" in node and not isinstance(node["capabilities"], list):
            return False
        if "endpoint" in node and node["endpoint"] is not None and not isinstance(node["endpoint"], str):
            return False
        return True
