import os
import difflib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)


def _safe(path):
    if not path:
        return None
    p = path.replace(BACKSLASH, '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        return None
    if '..' in p.split('/'):
        return None
    return p


def _read(val, is_file):
    if not is_file:
        return val or ''
    safe = _safe(val)
    if not safe:
        return None
    abs_path = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_path):
        return None
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return None


def run(params):
    a = params.get('a', '')
    b = params.get('b', '')
    a_is_file = bool(params.get('a_is_file', False))
    b_is_file = bool(params.get('b_is_file', False))
    if not a or not b:
        return {'success': False, 'error': 'need a and b'}
    text_a = _read(a, a_is_file)
    text_b = _read(b, b_is_file)
    if text_a is None:
        return {'success': False, 'error': 'a unreadable'}
    if text_b is None:
        return {'success': False, 'error': 'b unreadable'}
    lines_a = text_a.split(chr(10))
    lines_b = text_b.split(chr(10))
    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile='A', tofile='B', lineterm='', n=2))
    added = sum(1 for d in diff if d.startswith('+') and not d.startswith('+++'))
    removed = sum(1 for d in diff if d.startswith('-') and not d.startswith('---'))
    return {'success': True, 'identical': len(diff) == 0, 'added_lines': added, 'removed_lines': removed, 'diff': diff[:100], 'diff_total': len(diff), 'a_lines': len(lines_a), 'b_lines': len(lines_b)}
