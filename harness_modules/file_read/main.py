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


_RESOLVE_SKIP_DIRS = ('venv312', 'venv', 'node_modules', '.git', '__pycache__', '.backups', 'archive', 'training_data', 'seeds', 'static')


def _resolve_path(safe):
    """路径补全：裸文件名搜索同名文件。返回 (resolved, error_msg, candidates)"""
    full = os.path.join(REPO_ROOT, safe)
    if os.path.exists(full):
        return safe, None, []
    if '/' in safe or BACKSLASH in safe:
        return safe, None, []  # 含路径分隔符 → 不补全（让后续逻辑报文件不存在）
    # 裸文件名 → 搜索
    candidates = []
    _total = 0
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _RESOLVE_SKIP_DIRS]
        for f in filenames:
            if f == safe or (not os.path.splitext(safe)[1] and os.path.splitext(f)[0] == safe):
                _total += 1
                if len(candidates) < 5:
                    rel = os.path.relpath(os.path.join(dirpath, f), REPO_ROOT).replace(BACKSLASH, '/')
                    candidates.append(rel)
                break
    if _total == 1:
        return candidates[0], None, candidates
    elif _total > 1:
        _info = []
        for _c in sorted(candidates):
            try:
                _sz = os.path.getsize(os.path.join(REPO_ROOT, _c))
                _info.append(_c + " (" + str(_sz) + "B)")
            except Exception:
                _info.append(_c)
        _extra = ''
        if _total > len(candidates):
            _extra = '（仅显示前 ' + str(len(candidates)) + ' 个）'
        return safe, f'file_path "{safe}" 匹配到 ' + str(_total) + ' 个文件' + _extra + ': ' + " | ".join(_info) + '。请用完整路径。', candidates
    else:
        return safe, None, []  # 找不到 → 让原逻辑报"文件不存在"


def run(params):
    file_path = params.get('file_path', '')
    safe = _safe_path(file_path)
    if not safe:
        return {'success': False, 'error': 'file_path 不合法或指向敏感文件'}
    # v0.36.2: 路径自动补全
    _resolved, _resolve_err, _candidates = _resolve_path(safe)
    if _resolve_err:
        return {'success': False, 'error': _resolve_err, 'candidates': _candidates}
    if _resolved != safe:
        print(f'[file_read] path "{safe}" 未找到，自动解析为 "{_resolved}"')
        safe = _resolved
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
    _tail = int(params.get('tail_lines', 0))
    if _tail > 0:
        if _tail > total:
            _tail = total
        _selected = _all_lines[-_tail:] if _tail > 0 else []
        _content = ''.join(_selected)
        if len(_content) > 8000:
            _content = _content[:8000] + '...[已截断]'
        return {'success': True, 'file_path': safe, 'total_lines': total, 'mode': 'tail', 'tail_lines': _tail, 'content': _content}
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
