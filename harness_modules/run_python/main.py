import ast
import subprocess
import tempfile
import os
import sys

MAX_CODE_LEN = 50000
TIMEOUT = 120

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORBIDDEN_MODULES = {'subprocess', 'socket', 'ctypes', 'multiprocessing', 'signal'}
FORBIDDEN_NAMES = {'exec', 'eval'}

PREAMBLE_LINES = [
    '# === SAFE HELPERS ===',
    'import os as _real_os',
    '_real_open = open',
    '_REPO_ROOT = r"REPO_ROOT_PLACEHOLDER"',
    "_ALLOWED_DIRS = ('core/', 'static/', 'scripts/', 'docs/', 'harness_modules/', 'data/', 'logs/', 'launcher/')",
    "_FORBIDDEN_PARTS = ('.env', 'users.db', '.key', '.bin', '.pem', '.crt', 'secret_key', 'api_key_encryption')",
    '_MAX_READ = 5 * 1024 * 1024',
    '_MAX_WRITE = 5 * 1024 * 1024',
    'def _check_path(p):',
    '    if not isinstance(p, str):',
    "        raise ValueError('path must be str')",
    "    p = p.replace(chr(92), '/').strip()",
    "    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):",
    "        raise ValueError('absolute path forbidden: ' + p)",
    "    if '..' in p.split('/'):",
    "        raise ValueError('path traversal forbidden: ' + p)",
    '    lower = p.lower()',
    '    for part in _FORBIDDEN_PARTS:',
    '        if part in lower:',
    "            raise ValueError('forbidden path: ' + p)",
    '    if not any(p == d.rstrip("/") or p.startswith(d) for d in _ALLOWED_DIRS):',
    "        raise ValueError('path outside allowed dirs: ' + p)",
    '    return p',
    'def read_file(path):',
    '    safe = _check_path(path)',
    '    abs_p = _real_os.path.join(_REPO_ROOT, safe)',
    "    with _real_open(abs_p, 'r', encoding='utf-8') as f:",
    '        return f.read(_MAX_READ)',
    'def write_file(path, content):',
    '    safe = _check_path(path)',
    '    if len(content) > _MAX_WRITE:',
    "        raise ValueError('content too large')",
    '    abs_p = _real_os.path.join(_REPO_ROOT, safe)',
    "    with _real_open(abs_p, 'w', encoding='utf-8') as f:",
    '        f.write(content)',
    'def list_dir(path):',
    "    safe = _check_path(path) if path else '.'",
    '    return _real_os.listdir(_real_os.path.join(_REPO_ROOT, safe))',
    'def open(file, mode="r", *args, **kwargs):',
    '    safe = _check_path(file)',
    '    abs_p = _real_os.path.join(_REPO_ROOT, safe)',
    '    return _real_open(abs_p, mode, *args, **kwargs)',
    '# === USER CODE BELOW ===',
    '',
]

PREAMBLE = chr(10).join(PREAMBLE_LINES)


def _check_ast(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return 'syntax error: ' + str(e)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name.split('.')[0] in FORBIDDEN_MODULES:
                    return 'forbidden import: ' + n.name
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in FORBIDDEN_MODULES:
                return 'forbidden from: ' + node.module
        if isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                return 'forbidden name: ' + node.id
    return None


def run(params):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    code = params.get('code', '')
    if not code:
        return {'success': False, 'error': 'missing code'}
    if len(code) > MAX_CODE_LEN:
        return {'success': False, 'error': 'code too long'}
    err = _check_ast(code)
    if err:
        return {'success': False, 'error': err}
    tmp = None
    try:
        preamble = PREAMBLE.replace('REPO_ROOT_PLACEHOLDER', REPO_ROOT.replace(chr(92), '/'))
        full = preamble + code
        with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(full)
            tmp = f.name
        _env = os.environ.copy()
        _env['PYTHONPATH'] = REPO_ROOT
        _env['PYTHONIOENCODING'] = 'utf-8'
        _env['PYTHONUTF8'] = '1'
        r = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=TIMEOUT, encoding='utf-8', errors='replace', cwd=REPO_ROOT, env=_env)
        _err_msg = (r.stderr or '')[:500] if r.returncode != 0 else None
        return {
            'success': r.returncode == 0,
            'stdout': (r.stdout or '')[:3000],
            'stderr': (r.stderr or '')[:1000],
            'error': _err_msg,
            'returncode': r.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
