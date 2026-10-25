import os
import socket
import threading
import time
from typing import List, Callable, Optional

try:
    from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False

from core import config

def is_private_ip(ip: str) -> bool:
    """判断是否为有效的局域网私有 IP"""
    if not ip:
        return False
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        a, b, c, d = [int(p) for p in parts]
    except ValueError:
        return False
    # 排除回环、链路本地、保留地址
    if a == 127 or (a == 169 and b == 254):
        return False
    # 排除 198.18.0.0/15（网络测试保留）
    if a == 198 and b in (18, 19):
        return False
    # 私有地址范围
    if a == 10:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 192 and b == 168:
        return True
    return False

class NodeDiscovery:
    """基于 mDNS 的节点自动发现服务（后台线程运行）"""

    def __init__(self, on_peer_discovered: Optional[Callable[[str], None]] = None):
        if not ZEROCONF_AVAILABLE:
            print("zeroconf 库未安装，mDNS 发现功能禁用")
            self.enabled = False
            return

        self.enabled = config.ENABLE_MDNS
        if not self.enabled:
            return

        self.on_peer_discovered = on_peer_discovered
        self._lock = threading.Lock()
        self._discovered_peers = set()
        self._stop_event = threading.Event()
        self._thread = None
        self.zeroconf = None
        self.info = None
        self.browser = None
        self.local_ip = None

    def _get_local_ip(self) -> Optional[str]:
        """获取本机局域网 IP，优先使用主机名解析并过滤有效地址；失败返回 None"""
        # 方法1：主机名解析
        try:
            hostname = socket.gethostname()
            ip_list = socket.gethostbyname_ex(hostname)[2]
            for ip in ip_list:
                if is_private_ip(ip):
                    return ip
        except Exception:
            pass

        # 方法2：UDP 连接外部地址
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if is_private_ip(ip):
                return ip
        except Exception:
            pass

        return None

    def _run(self):
        """在后台线程中运行 mDNS 注册与监听"""
        try:
            self.zeroconf = Zeroconf()
            # 使用 start() 中已获取的 local_ip
            local_ip = self.local_ip
            port = int(os.environ.get("SASES_PORT", "8001"))

            self.info = ServiceInfo(
                config.MDNS_SERVICE_TYPE,
                f"{config.NODE_ID}.{config.MDNS_SERVICE_TYPE}",
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties={"node_id": config.NODE_ID, "node_name": config.NODE_NAME}
            )
            self.zeroconf.register_service(self.info)

            class Listener(ServiceListener):
                def __init__(self, outer):
                    self.outer = outer

                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        self.outer._handle_new_service(info)

                def remove_service(self, zc, type_, name):
                    pass

                def update_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        self.outer._handle_new_service(info)

            self.browser = ServiceBrowser(self.zeroconf, config.MDNS_SERVICE_TYPE, listener=Listener(self))
            print(f"mDNS 发现服务已启动，广播服务: {self.info.name} @ {local_ip}:{port}")

            # 保持线程运行，直到收到停止信号
            while not self._stop_event.is_set():
                time.sleep(1)
        except Exception as e:
            print(f"mDNS 服务异常: {e}")

    def start(self):
        """启动 mDNS 服务。如果无法获取有效局域网 IP，则自动禁用。"""
        if not self.enabled or not ZEROCONF_AVAILABLE:
            return

        # 先获取有效 IP
        self.local_ip = self._get_local_ip()
        if not self.local_ip:
            print("未找到有效局域网 IP，mDNS 发现服务已自动禁用。")
            self.enabled = False
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _handle_new_service(self, info):
        """处理新发现的服务"""
        if not info or not info.addresses:
            return
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        # 排除自己
        if info.name.startswith(config.NODE_ID):
            return
        peer_url = f"http://{ip}:{port}"
        with self._lock:
            if peer_url not in self._discovered_peers:
                self._discovered_peers.add(peer_url)
                print(f"发现新节点: {peer_url}")
                if self.on_peer_discovered:
                    try:
                        self.on_peer_discovered(peer_url)
                    except Exception as e:
                        print(f"处理新节点失败: {e}")

    def stop(self):
        if not self.enabled or not ZEROCONF_AVAILABLE:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self.zeroconf:
            try:
                if self.info:
                    self.zeroconf.unregister_service(self.info)
                if self.browser:
                    self.browser.cancel()
                self.zeroconf.close()
            except Exception as e:
                print(f"关闭 zeroconf 失败: {e}")
        print("mDNS 发现服务已停止")
