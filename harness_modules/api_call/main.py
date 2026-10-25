import json
import urllib.request
import urllib.parse
import ipaddress
import socket

TIMEOUT = 60
MAX_BODY = 15000
FORBIDDEN_HEADERS = {'host', 'connection', 'content-length'}


def _is_private_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return True
    if parsed.scheme not in ('http', 'https'):
        return True
    host = parsed.hostname
    if not host:
        return True
    if host in ('localhost', '127.0.0.1', '0.0.0.0'):
        return True
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return True
    except ValueError:
        pass
    try:
        resolved = socket.gethostbyname(host)
        ip = ipaddress.ip_address(resolved)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return True
    except Exception:
        pass
    return False


def run(params):
    url = (params.get('url') or '').strip()
    if not url:
        return {'success': False, 'error': 'missing url'}
    if _is_private_url(url):
        return {'success': False, 'error': 'URL 禁止内网或非法协议'}
    method = (params.get('method') or 'GET').upper()
    if method not in ('GET', 'POST', 'PUT', 'DELETE', 'PATCH'):
        return {'success': False, 'error': 'unsupported method: ' + method}
    headers = params.get('headers') or {}
    if not isinstance(headers, dict):
        return {'success': False, 'error': 'headers 必须是 dict'}
    clean_headers = {}
    for k, v in headers.items():
        if str(k).lower() in FORBIDDEN_HEADERS:
            continue
        clean_headers[str(k)] = str(v)
    body = params.get('body')
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            if 'Content-Type' not in clean_headers and 'content-type' not in clean_headers:
                clean_headers['Content-Type'] = 'application/json'
        else:
            data = str(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in clean_headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            raw = resp.read(MAX_BODY * 2)
            text = raw.decode('utf-8', errors='replace')
            if len(text) > MAX_BODY:
                text = text[:MAX_BODY] + '...[truncated]'
            return {'success': True, 'status': status, 'body': text}
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read(1000).decode('utf-8', errors='replace')
        except Exception:
            err_body = ''
        return {'success': False, 'status': e.code, 'error': str(e), 'body': err_body}
    except Exception as e:
        return {'success': False, 'error': str(e)}