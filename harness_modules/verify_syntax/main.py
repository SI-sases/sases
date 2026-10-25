import os, ast, subprocess, shutil, re
import ast
import subprocess
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED_DIRS = ('core/', 'static/', 'scripts/', 'docs/', 'harness_modules/', 'data/', 'logs/', 'launcher/')
FORBIDDEN = ('.env', 'users.db', '.key', '.bin', '.pem', '.crt', 'secret_key', 'api_key_encryption')
BACKUP_DIR = '.backups'
UI_PREFIXES = ('render', 'open', 'show', 'hide', 'update', 'toggle', 'close')


import re as _re2
_EXTERNAL_RE2 = _re2.compile(r'^([A-Za-z]):/')


def _is_external_safe(p):
    m = _EXTERNAL_RE2.match(p)
    if not m:
        return False
    return m.group(1).upper() != 'C'


import re as _re2
_EXTERNAL_RE2 = _re2.compile(r'^([A-Za-z]):/')


def _is_external_safe(p):
    m = _EXTERNAL_RE2.match(p)
    if not m:
        return False
    return m.group(1).upper() != 'C'


def _check(p):
    if not isinstance(p, str):
        raise ValueError('path must be str')
    p = p.replace(chr(92), '/').strip()
    if not _is_external_safe(p):
        if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
            raise ValueError('absolute path forbidden')
        if '..' in p.split('/'):
            raise ValueError('path traversal forbidden')
    lower = p.lower()
    for part in FORBIDDEN:
        if part in lower:
            raise ValueError('forbidden path')
    if not _is_external_safe(p) and not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError('outside allowed dirs')
    return p


def _find_latest_backup(safe_path):
    safe_name = safe_path.replace('/', '__').replace(chr(92), '__')
    bdir = os.path.join(REPO_ROOT, BACKUP_DIR)
    if not os.path.isdir(bdir):
        return None
    matches = [f for f in os.listdir(bdir) if f.startswith(safe_name + '.')]
    if not matches:
        return None
    matches.sort(reverse=True)
    return os.path.join(bdir, matches[0])


def _verify_py(abs_p):
    try:
        with open(abs_p, 'r', encoding='utf-8') as f:
            src = f.read()
        ast.parse(src)
        return True, ''
    except SyntaxError as e:
        return False, 'line ' + str(e.lineno) + ': ' + str(e.msg)
    except Exception as e:
        return False, str(e)


def _verify_js(abs_p):
    try:
        r = subprocess.run(['node', '--check', abs_p], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
        if r.returncode == 0:
            return True, ''
        return False, (r.stderr or '')[:500]
    except FileNotFoundError:
        return None, 'node not available'
    except Exception as e:
        return None, str(e)


def _check_undefined_calls(content, ext):
    import re as _re
    if ext == '.js':
        calls = set()
        for prefix in UI_PREFIXES:
            for m in _re.finditer(r'(?<![A-Za-z0-9_.])' + prefix + r'[A-Z][A-Za-z0-9_]*\s*\(', content):
                calls.add(m.group(0)[:-1].strip())
        if not calls:
            return []
        defs = set()
        for m in _re.finditer(r'import\s*\{([^}]+)\}', content):
            for name in m.group(1).split(','):
                n = name.strip().split(' as ')[-1].strip()
                if n:
                    defs.add(n)
        for m in _re.finditer(r'import\s+([A-Za-z_]\w*)\s+from', content):
            defs.add(m.group(1))
        for m in _re.finditer(r'function\s+([A-Za-z_]\w*)', content):
            defs.add(m.group(1))
        for m in _re.finditer(r'(?:const|let|var)\s+([A-Za-z_]\w*)\s*=', content):
            defs.add(m.group(1))
        for m in _re.finditer(r'window\.([A-Za-z_]\w*)\s*=', content):
            defs.add(m.group(1))
        return sorted(calls - defs)
    elif ext == '.py':
        try:
            tree = ast.parse(content)
        except Exception:
            return []
        calls = set()
        defs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                n = node.func.id
                for prefix in UI_PREFIXES:
                    if n.startswith(prefix) and len(n) > len(prefix) and n[len(prefix)].isupper():
                        calls.add(n)
                        break
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs.add(node.name)
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    defs.add(a.asname or a.name)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    defs.add(a.asname or a.name.split('.')[0])
        return sorted(calls - defs)
    return []


def _check_open_subpage_return_action(content):
    """扫描 .js 文件里所有 openSubpage 调用，检查是否传了 returnAction。"""
    import re as _re
    warnings = []
    pattern = _re.compile(r'(?:window\.)?openSubpage\s*\(')
    for m in pattern.finditer(content):
        start = m.end()
        window_end = min(len(content), start + 500)
        window_text = content[start:window_end]
        if 'returnAction' not in window_text:
            line_no = content[:m.start()].count(chr(10)) + 1
            line_end = content.find(chr(10), m.start())
            if line_end < 0:
                line_end = len(content)
            line_text = content[m.start():line_end].strip()[:80]
            warnings.append('line ' + str(line_no) + ': ' + line_text)
    return warnings



def run(params):
    fp = params.get('file_path', '')
    if not fp:
        return {'success': False, 'error': 'missing file_path'}
    try:
        safe = _check(fp)
    except Exception as e:
        return {'success': False, 'error': str(e)}
    abs_p = safe if _is_external_safe(safe) else os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_p):
        return {'success': False, 'error': 'not found: ' + safe}
    ext = os.path.splitext(safe)[1].lower()
    if ext == '.py':
        ok, err = _verify_py(abs_p)
        supported = True
    elif ext == '.js':
        ok, err = _verify_js(abs_p)
        supported = ok is not None
        if ok is None:
            return {'success': True, 'file_path': safe, 'skipped': True, 'reason': err}
    else:
        return {'success': True, 'file_path': safe, 'skipped': True, 'reason': 'ext not checked: ' + ext}
    # success 始终 True（工具调用成功）；syntax_ok 才是结论
    result = {'success': True, 'file_path': safe, 'syntax_ok': bool(ok)}

    if params.get('check_undefined', True):
        try:
            with open(abs_p, 'r', encoding='utf-8') as f:
                _content = f.read(200 * 1024)
            _missing = _check_undefined_calls(_content, ext)
            if _missing:
                result['undefined_calls'] = _missing
                if ok:
                    ok = False
                    err = 'undefined calls: ' + ', '.join(_missing[:5])
                    result['syntax_ok'] = False
        except Exception as _ce:
            result['undefined_check_error'] = str(_ce)


    if ext == '.js':
        try:
            with open(abs_p, 'r', encoding='utf-8') as _wf:
                _js_content = _wf.read(200 * 1024)
            _sub_warns = _check_open_subpage_return_action(_js_content)
            if _sub_warns:
                result['warnings'] = _sub_warns
        except Exception as _we:
            result['warning_check_error'] = str(_we)

    auto_rollback = params.get('auto_rollback', True)
    if not ok and auto_rollback:
        bak = _find_latest_backup(safe)
        if bak:
            try:
                shutil.copy2(bak, abs_p)
                result['rolled_back'] = True
                result['restored_from'] = os.path.relpath(bak, REPO_ROOT).replace(chr(92), '/')
            except Exception as _e:
                result['rollback_error'] = str(_e)

    if not ok:
        result['error'] = err
        bak = _find_latest_backup(safe)
        if bak:
            result['latest_backup'] = os.path.relpath(bak, REPO_ROOT).replace(chr(92), '/')
            result['hint'] = 'from run_python: import shutil; shutil.copy2(\'' + result['latest_backup'] + '\', \'' + safe + '\')'
    return result