import os
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
BACKUP_DIR = '.backups'
FORBIDDEN_PARTS = ('.env', 'users.db', 'secret_key', 'api_key_encryption')
FORBIDDEN_EXT = ('.key', '.bin', '.pem', '.crt', '.db', '.sqlite')
SELF_PROTECTED = (
    'harness_modules/file_patch/main.py',
    'harness_modules/file_patch/manifest.json',
    'core/services/executor_service.py',
)
import re as _re
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
            return None
        if '..' in p.split('/'):
            return None
        if p in SELF_PROTECTED:
            return None
    lower = p.lower()
    for part in FORBIDDEN_PARTS:
        if part in lower:
            return None
    ext = os.path.splitext(p)[1].lower()
    if ext in FORBIDDEN_EXT:
        return None
    return p


def _backup(abs_path, safe):
    try:
        if not os.path.exists(abs_path):
            return None
        bdir = os.path.join(REPO_ROOT, BACKUP_DIR)
        os.makedirs(bdir, exist_ok=True)
        safe_name = safe.replace('/', '__')
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        bpath = os.path.join(bdir, safe_name + '.' + ts + '.bak')
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            data = f.read()
        with open(bpath, 'w', encoding='utf-8') as f:
            f.write(data)
        return bpath
    except Exception:
        return None


def run(params):
    file_path = params.get('file_path', '')
    safe = _safe_path(file_path)
    if not safe:
        return {'success': False, 'error': 'file_path illegal or sensitive'}
    try:
        start_line = int(params.get('start_line', 0))
        end_line = int(params.get('end_line', 0))
    except Exception:
        return {'success': False, 'error': 'start_line / end_line must be int'}
    new_content = params.get('new_content', '')
    if start_line < 1:
        return {'success': False, 'error': 'start_line must be >= 1'}
    if end_line < start_line - 1:
        return {'success': False, 'error': 'end_line must be >= start_line - 1'}
    abs_path = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_path):
        return {'success': False, 'error': 'file not found: ' + safe}
    if os.path.isdir(abs_path):
        return {'success': False, 'error': safe + ' is a directory'}
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return {'success': False, 'error': str(e)}
    total = len(lines)
    if start_line > total + 1:
        return {'success': False, 'error': 'start_line=' + str(start_line) + ' exceeds total ' + str(total)}
    if end_line > total:
        end_line = total
    backup_path = _backup(abs_path, safe)
    is_insert = (start_line == end_line + 1)
    before = lines[:start_line - 1]
    after = lines[end_line:]
    nc = new_content
    if nc and not nc.endswith(chr(10)):
        nc = nc + chr(10)
    new_lines = before + ([nc] if nc else []) + after
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
    except Exception as e:
        return {'success': False, 'error': str(e)}
    replaced = end_line - start_line + 1 if not is_insert else 0
    return {'success': True, 'file_path': safe, 'mode': 'insert' if is_insert else 'replace', 'start_line': start_line, 'end_line': end_line, 'replaced_lines': replaced, 'new_total_lines': len(new_lines), 'backup': backup_path}
