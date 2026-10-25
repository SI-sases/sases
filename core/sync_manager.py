import json
import time
from typing import Dict, Any, List, Optional

import httpx

from core import config
from core.node_registry import NodeRegistry

class SyncManager:
    """节点同步与注册到 peer"""

    def __init__(self, node_registry: NodeRegistry):
        self.node_registry = node_registry

    def sync_from_peer(self, peer_url: str) -> dict:
        url = f"{peer_url.rstrip('/')}/space/nodes"
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                remote_nodes = response.json()
                added = 0
                invalid = 0
                if not isinstance(remote_nodes, list):
                    return {"success": False, "error": "Invalid response format from peer"}
                for node in remote_nodes:
                    if not isinstance(node, dict) or not self.node_registry.is_valid_node(node):
                        invalid += 1
                        continue
                    node_id = node.get("node_id")
                    if node_id and not self.node_registry.get_node(node_id):
                        # 通过 registry 添加，但不改变其初始状态
                        self.node_registry.register_node(
                            node_id=node_id,
                            name=node["name"],
                            description=node.get("description", ""),
                            node_type=node.get("node_type", "harness"),
                            capabilities=node.get("capabilities", []),
                            endpoint=node.get("endpoint"),
                            icon=node.get("icon"),
                            owner_id=node.get("owner_id", "remote")
                        )
                        added += 1
                return {
                    "success": True,
                    "added": added,
                    "invalid": invalid,
                    "total_local": len(self.node_registry.list_nodes())
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_to_peer(self, peer_url: str) -> dict:
        url = f"{peer_url.rstrip('/')}/space/register_node_external"
        self_node = self.node_registry.get_node(config.NODE_ID)
        if not self_node:
            return {"success": False, "error": "Local node not registered"}
        payload = {
            "node_id": self_node["node_id"],
            "name": self_node["name"],
            "description": self_node["description"],
            "node_type": self_node["node_type"],
            "capabilities": self_node["capabilities"],
            "endpoint": self_node.get("endpoint"),
            "icon": self_node.get("icon"),
            "owner_id": self_node.get("owner_id")
        }
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=5) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
