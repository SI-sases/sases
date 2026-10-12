import os
import re as _re
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
FORBIDDEN_PARTS = ('.env', 'users.db', 'secret_key', 'api_key_encryption')
FORBIDDEN_EXT = ('.key', '.bin', '.pem', '.crt', '.db', '.sqlite')
_EXTERNAL_RE = _re.compile(r'^([A-Za-z]):/')


def _is_external(p):
    m = _EXTERNAL_RE.match(p)
    if not m:
        return False
    return m.group(1).upper() != 'C'


def _safe_path(p):
    if not p:
        return None
    p = p.replace(BACKSLASH, '/').strip()
    if not _is_external(p):
        if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
            _root_norm = REPO_ROOT.replace(BACKSLASH, '/').rstrip('/').lower()
            if not p.lower().startswith(_root_norm + '/'):
                return None
        if '..' in p.split('/'):
            return None
    lower = p.lower()
    for part in FORBIDDEN_PARTS:
        if part in lower:
            return None
    ext = os.path.splitext(p)[1].lower()
    if ext in FORBIDDEN_EXT:
        return None
    return p


def run(params):
    file_path = params.get('file_path', '')
    safe = _safe_path(file_path)
    if not safe:
        return {'success': False, 'error': 'file_path 不合法或指向敏感文件'}
    abs_path = safe if os.path.isabs(safe) else os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_path):
        return {'success': False, 'error': '文件不存在: ' + safe}
    if os.path.isdir(abs_path):
        return {'success': False, 'error': safe + ' 是目录，请用 dir_tree'}
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            _all_lines = f.readlines()
    except Exception as e:
        return {'success': False, 'error': str(e)}
    total = len(_all_lines)
    _lines_param = params.get('lines')
    if _lines_param:
        try:
            _targets = [int(x) for x in _lines_param] if isinstance(_lines_param, list) else [int(_lines_param)]
        except Exception:
            return {'success': False, 'error': 'lines 必须是整数或整数列表'}
        _out = []
        for _ln in _targets:
            if 1 <= _ln <= total:
                _out.append(str(_ln) + ': ' + _all_lines[_ln - 1].rstrip())
            else:
                _out.append(str(_ln) + ': [超出范围]')
        return {'success': True, 'file_path': safe, 'total_lines': total, 'mode': 'lines', 'content': chr(10).join(_out)}
    _grep = params.get('grep')
    if _grep:
        try:
            _rx = _re.compile(_grep)
        except Exception:
            _rx = None
        _hits = []
        for _ln, _line in enumerate(_all_lines, 1):
            _m = _rx.search(_line) if _rx else (_grep in _line)
            if _m:
                _hits.append(str(_ln) + ': ' + _line.rstrip())
        _limit = int(params.get('max_results', 50))
        _total_hits = len(_hits)
        if _total_hits > _limit:
            _hits = _hits[:_limit]
            _hits.append('...[还有 ' + str(_total_hits - _limit) + ' 条，已截断]')
        return {'success': True, 'file_path': safe, 'total_lines': total, 'mode': 'grep', 'grep': _grep, 'count': _total_hits, 'content': chr(10).join(_hits)}
    max_lines = int(params.get('max_lines', 300))
    if max_lines < 1 or max_lines > 1000:
        max_lines = 200
    offset = int(params.get('offset', 0))
    if offset < 0:
        offset = 0
    selected = _all_lines[offset:offset + max_lines]
    content = ''.join(selected)
    if len(content) > 8000:
        content = content[:8000] + '...[已截断]'
    return {'success': True, 'file_path': safe, 'total_lines': total, 'showing_from': offset + 1, 'showing_to': min(offset + max_lines, total), 'content': content}
