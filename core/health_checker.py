import httpx
from typing import Dict, Any, List, Optional

from core import config
from core.node_registry import NodeRegistry

class HealthChecker:
    """节点健康检查"""

    def __init__(self, node_registry: NodeRegistry):
        self.node_registry = node_registry

    def check_node_health(self, node_id: str) -> bool:
        node = self.node_registry.get_node(node_id)
        if not node or not node.get("endpoint"):
            return False
        endpoint = node["endpoint"].rstrip("/")
        health_url = f"{endpoint}/space/health"
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=3) as client:
                response = client.get(health_url, headers=headers)
                if response.status_code == 200:
                    self.node_registry.update_node_status(node_id, "online")
                    return True
                else:
                    self.node_registry.update_node_status(node_id, "offline")
                    return False
        except Exception:
            self.node_registry.update_node_status(node_id, "offline")
            return False

    def update_all_nodes_health(self):
        nodes = self.node_registry.list_nodes()
        for node in nodes:
            if node.get("endpoint"):
                self.check_node_health(node["node_id"])
