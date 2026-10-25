import threading
from typing import Dict, Any, List, Optional

import httpx

from core.harness_runtime import harness_runtime
from core import config
from core.node_registry import NodeRegistry
from core.sync_manager import SyncManager
from core.health_checker import HealthChecker

class SpaceService:
    """空间节点服务门面，组合节点注册、同步、健康检查等功能"""

    def __init__(self):
        self.node_registry = NodeRegistry()
        self.sync_manager = SyncManager(self.node_registry)
        self.health_checker = HealthChecker(self.node_registry)

        # 后台线程
        self._sync_thread = None
        self._stop_sync = threading.Event()
        self._health_thread = None
        self._stop_health = threading.Event()

    # ---------- 节点注册与查询 ----------
    def register_node(self, node_id: str, name: str, description: str,
                      node_type: str = "harness", capabilities: List[str] = None,
                      endpoint: str = None, icon: str = None, owner_id: str = "system") -> Dict[str, Any]:
        return self.node_registry.register_node(node_id, name, description, node_type, capabilities, endpoint, icon, owner_id)

    def list_nodes(self, node_type: str = None) -> List[Dict[str, Any]]:
        return self.node_registry.list_nodes(node_type)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.node_registry.get_node(node_id)

    def update_reputation(self, node_id: str, success: bool):
        self.node_registry.update_reputation(node_id, success)

    def update_node_status(self, node_id: str, status: str):
        self.node_registry.update_node_status(node_id, status)

    # ---------- 远程调用 ----------
    def invoke_remote_node(self, node_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        node = self.get_node(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}

        if node.get("node_type") == "harness" and not node.get("endpoint"):
            resp = harness_runtime.invoke_tool(node_id, params)
            self.update_reputation(node_id, resp.success)
            return {
                "success": resp.success,
                "result": resp.result if resp.success else None,
                "error": resp.error if not resp.success else None
            }

        endpoint = node.get("endpoint")
        if not endpoint:
            return {"success": False, "error": "Node has no endpoint for remote invocation"}

        url = f"{endpoint.rstrip('/')}/harness/invoke"
        payload = {"module_id": node_id, "params": params}
        headers = {}
        if config.NODE_TOKEN:
            headers["X-Node-Token"] = config.NODE_TOKEN
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                success = data.get("success", False)
                self.update_reputation(node_id, success)
                return data
        except Exception as e:
            self.update_reputation(node_id, False)
            return {"success": False, "error": f"Remote call failed: {e}"}

    # ---------- 同步与健康 ----------
    def sync_from_peer(self, peer_url: str) -> dict:
        return self.sync_manager.sync_from_peer(peer_url)

    def register_to_peer(self, peer_url: str) -> dict:
        return self.sync_manager.register_to_peer(peer_url)

    def check_node_health(self, node_id: str) -> bool:
        return self.health_checker.check_node_health(node_id)

    def sync_all_peers(self):
        peers = config.PEER_NODES
        if not peers:
            return
        for peer in peers:
            result = self.sync_from_peer(peer)
            if result.get("success"):
                print(f"同步 {peer} 成功，新增节点 {result.get('added', 0)}")
            else:
                print(f"同步 {peer} 失败: {result.get('error')}")
            reg_result = self.register_to_peer(peer)
            if reg_result.get("success") or "Node registered" in str(reg_result):
                print(f"向 {peer} 注册成功")
            else:
                print(f"向 {peer} 注册失败: {reg_result.get('error')}")
        # 同步后更新所有节点健康状态
        self.health_checker.update_all_nodes_health()

    # ---------- 后台任务 ----------
    def start_auto_sync(self, interval: int = 300):
        if self._sync_thread and self._sync_thread.is_alive():
            return
        self._stop_sync.clear()
        self._sync_thread = threading.Thread(target=self._auto_sync_loop, args=(interval,), daemon=True)
        self._sync_thread.start()
        print(f"自动同步线程已启动，间隔 {interval} 秒")

    def stop_auto_sync(self):
        self._stop_sync.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
            self._sync_thread = None
        print("自动同步线程已停止")

    def _auto_sync_loop(self, interval):
        while not self._stop_sync.is_set():
            self.sync_all_peers()
            self._stop_sync.wait(interval)

    def start_health_check(self, interval: int = 60):
        if self._health_thread and self._health_thread.is_alive():
            return
        self._stop_health.clear()
        self._health_thread = threading.Thread(target=self._health_check_loop, args=(interval,), daemon=True)
        self._health_thread.start()
        print(f"健康检查线程已启动，间隔 {interval} 秒")

    def stop_health_check(self):
        self._stop_health.set()
        if self._health_thread:
            self._health_thread.join(timeout=5)
            self._health_thread = None
        print("健康检查线程已停止")

    def _health_check_loop(self, interval):
        while not self._stop_health.is_set():
            self.health_checker.update_all_nodes_health()
            self._stop_health.wait(interval)

# 全局单例
space_service = SpaceService()
