"""文件复制工具（跨盘）"""
import os
import shutil
import re as _re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXTERNAL_RE = _re.compile(r'^([A-Za-z]):/')
ALLOWED_DIRS = ("static/", "core/", "scripts/", "docs/", "harness_modules/", "data/", "logs/", "launcher/")
FORBIDDEN_PARTS = ('.env', 'users.db', 'secret_key', 'api_key_encryption', '.backups')
FORBIDDEN_EXT = ('.key', '.bin', '.pem', '.crt', '.db', '.sqlite')


def _is_external(p):
    m = _EXTERNAL_RE.match(p)
    if not m:
        return False
    return m.group(1).upper() != 'C'


def _validate(p, is_src):
    if not p or not isinstance(p, str):
        raise ValueError('path must be non-empty str')
    p = p.replace('\\', '/').strip()
    lower = p.lower()
    for part in FORBIDDEN_PARTS:
        if part in lower:
            raise ValueError('forbidden file: ' + p)
    ext = os.path.splitext(p)[1].lower()
    if ext in FORBIDDEN_EXT:
        raise ValueError('forbidden ext: ' + ext)
    if _is_external(p):
        return p
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        raise ValueError('absolute path forbidden: ' + p)
    if '..' in p.split('/'):
        raise ValueError('path traversal forbidden: ' + p)
    if not is_src and not any(p.startswith(d) for d in ALLOWED_DIRS):
        raise ValueError('dst outside allowed dirs: ' + p)
    return p


def _abs(p):
    return p if _is_external(p) else os.path.join(REPO_ROOT, p)


def run(params):
    src = params.get('src') or params.get('src_path') or ''
    dst = params.get('dst') or params.get('dst_path') or ''
    overwrite = bool(params.get('overwrite', False))
    src_safe = _validate(src, is_src=True)
    dst_safe = _validate(dst, is_src=False)
    src_abs = _abs(src_safe)
    dst_abs = _abs(dst_safe)
    if not os.path.exists(src_abs):
        return {'success': False, 'error': 'src not found: ' + src_safe}
    if os.path.exists(dst_abs) and not overwrite:
        return {'success': False, 'error': 'dst exists (pass overwrite=true): ' + dst_safe}
    parent = os.path.dirname(dst_abs)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copy2(src_abs, dst_abs)
    return {'success': True, 'src': src_safe, 'dst': dst_safe, 'size': os.path.getsize(dst_abs)}
