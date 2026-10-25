import os
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED_DIRS = ('core/', 'static/', 'scripts/', 'docs/', 'harness_modules/', 'data/', 'logs/', 'launcher/')
FORBIDDEN = ('.env', 'users.db', '.key', '.bin', '.pem', '.crt', 'secret_key', 'api_key_encryption')

def _check(p):
    if not isinstance(p, str):
        raise ValueError('path must be str')
    p = p.replace(chr(92), '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        raise ValueError('absolute path forbidden')
    if '..' in p.split('/'):
        raise ValueError('path traversal forbidden')
    lower = p.lower()
    for part in FORBIDDEN:
        if part in lower:
            raise ValueError('forbidden path')
    if not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError('outside allowed dirs')
    return p

def run(params):
    fp = params.get('file_path', '')
    if not fp:
        return {'success': False, 'error': 'missing file_path'}
    try:
        safe = _check(fp)
    except Exception as e:
        return {'success': False, 'error': str(e)}
    abs_p = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_p):
        return {'success': False, 'error': 'not found: ' + safe}
    try:
        with open(abs_p, 'r', encoding='utf-8') as f:
            content = f.read(200 * 1024)
    except Exception as e:
        return {'success': False, 'error': 'read failed: ' + str(e)}
    # success 始终 True（工具调用成功）；checks 结果才是结论
    result = {'success': True, 'file_path': safe, 'total_lines': len(content.split(chr(10))), 'all_checks_passed': True, 'checks': []}
    inc = params.get('expect_contains') or []
    if isinstance(inc, str): inc = [inc]
    for s in inc:
        if not s: continue
        found = s in content
        result['checks'].append({'type': 'contains', 'pattern': s[:80], 'found': found})
        if not found: result['all_checks_passed'] = False
    exc = params.get('expect_not_contains') or []
    if isinstance(exc, str): exc = [exc]
    for s in exc:
        if not s: continue
        found = s in content
        result['checks'].append({'type': 'not_contains', 'pattern': s[:80], 'found': found})
        if found: result['all_checks_passed'] = False
    return result