import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
SKIP_DIRS = ('venv312', 'venv', 'node_modules', '.git', '__pycache__', '.backups', 'archive', 'training_data', 'seeds', 'logs', 'backups')


def _safe_path(p):
    if not p or p == '.':
        return '.'
    p = p.replace(BACKSLASH, '/').strip().rstrip('/')
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        return None
    if '..' in p.split('/'):
        return None
    return p


def _walk(root, rel, depth, max_depth, lines):
    if depth > max_depth:
        return
    try:
        entries = sorted(os.listdir(os.path.join(root, rel)))
    except Exception:
        return
    for e in entries:
        if e in SKIP_DIRS:
            continue
        full = os.path.join(root, rel, e)
        new_rel = os.path.join(rel, e) if rel != '.' else e
        rel_display = new_rel.replace(BACKSLASH, '/')
        indent = '  ' * depth
        if os.path.isdir(full):
            lines.append(indent + rel_display + '/')
            _walk(root, new_rel, depth + 1, max_depth, lines)
        else:
            lines.append(indent + rel_display)


def run(params):
    path = params.get('path', '.')
    safe = _safe_path(path)
    if safe is None:
        return {'success': False, 'error': 'path 不合法'}
    abs_path = os.path.join(REPO_ROOT, safe) if safe != '.' else REPO_ROOT
    if not os.path.exists(abs_path):
        return {'success': False, 'error': '路径不存在: ' + str(path)}
    if not os.path.isdir(abs_path):
        return {'success': False, 'error': str(path) + ' 不是目录，请用 file_read'}
    max_depth = int(params.get('max_depth', 2))
    if max_depth < 1 or max_depth > 4:
        max_depth = 2
    lines = []
    _walk(REPO_ROOT, safe, 1, max_depth, lines)
    if len(lines) > 300:
        lines = lines[:300] + ['...(已截断，共 ' + str(len(lines)) + ' 项)']
    return {'success': True, 'path': safe, 'max_depth': max_depth, 'tree': chr(10).join(lines)}