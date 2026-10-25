# harness_modules/web_fetch/main.py
import re
import socket
import ipaddress
from urllib.parse import urlparse
import requests

MAX_SIZE = 100 * 1024  # 100KB
TIMEOUT = 30
MAX_TEXT_LEN = 2000


def _is_private_host(host):
    """检查 host 是否指向内网地址"""
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        try:
            ip_str = socket.gethostbyname(host)
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except Exception:
            return True


def _strip_html(html):
    """去除 HTML 标签，返回纯文本"""
    html = re.sub(r'<script.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def run(params=None):
    if params is None:
        params = {}
    url = (params.get("url") or "").strip()
    if not url:
        return {"success": False, "error": "缺少 url 参数"}

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"success": False, "error": f"不支持的协议: {parsed.scheme}"}

    host = parsed.hostname
    if not host:
        return {"success": False, "error": "URL 缺少 host"}

    if _is_private_host(host):
        return {"success": False, "error": f"禁止访问内网地址: {host}"}

    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": "SASES/0.15.0"},
            stream=True
        )
        resp.raise_for_status()

        content_length = int(resp.headers.get("content-length", 0))
        if content_length > MAX_SIZE:
            return {"success": False, "error": f"响应过大: {content_length} 字节"}

        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_SIZE:
                return {"success": False, "error": "响应超过 100KB 限制"}

        encoding = resp.encoding or "utf-8"
        try:
            html = content.decode(encoding, errors="replace")
        except Exception:
            html = content.decode("utf-8", errors="replace")

        text = _strip_html(html)[:MAX_TEXT_LEN]

        return {
            "success": True,
            "url": url,
            "status_code": resp.status_code,
            "text": text,
            "length": len(text)
        }
    except requests.Timeout:
        return {"success": False, "error": "请求超时"}
    except requests.RequestException as e:
        return {"success": False, "error": f"请求失败: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"异常: {str(e)}"}
