import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
SKIP_DIRS = ('venv312', 'venv', 'node_modules', '.git', '__pycache__', '.backups', 'archive', 'training_data', 'seeds')
SKIP_EXT = ('.pyc', '.zip', '.safetensors', '.onnx', '.db', '.bin', '.key', '.png', '.jpg', '.ico', '.bak', '.bak_acceptance')
SKIP_NAME_MARKERS = ('.db.bak', '.db.bak_', '.bak.')
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2MB


def _iter_files(root, rel_base, file_ext):
    _full_base = os.path.join(root, rel_base)
    if os.path.isfile(_full_base):
        _ext = os.path.splitext(_full_base)[1].lower()
        if _ext not in SKIP_EXT and (not file_ext or _ext == file_ext):
            yield _full_base, rel_base
        return
    for dirpath, dirnames, filenames in os.walk(_full_base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if any(m in fn for m in SKIP_NAME_MARKERS):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXT:
                continue
            if file_ext and ext != file_ext:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(BACKSLASH, '/')
            yield full, rel


def _resolve_path(safe):
    """路径补全：裸文件名搜索同名文件。返回 (resolved, error_msg, candidates)"""
    full = os.path.join(REPO_ROOT, safe)
    if os.path.exists(full):
        return safe, None, []
    # 含路径分隔符 → 不补全
    if '/' in safe or BACKSLASH in safe:
        return safe, f'path 不存在: {safe}', []
    # 裸文件名 → 搜索
    candidates = []
    _total = 0
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if safe in filenames:
            _total += 1
            if len(candidates) < 5:
                rel = os.path.relpath(os.path.join(dirpath, safe), REPO_ROOT).replace(BACKSLASH, '/')
                candidates.append(rel)
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
        return safe, f'path "{safe}" 匹配到 ' + str(_total) + ' 个文件' + _extra + ': ' + " | ".join(_info) + '。请用完整路径。', candidates
    else:
        return safe, f'path 不存在: {safe}', []


def run(params):
    pattern = params.get('pattern', '').strip()
    if not pattern:
        return {'success': False, 'error': '缺少 pattern'}
    if len(pattern) > 100:
        return {'success': False, 'error': 'pattern 太长（>100）'}
    path = params.get('path', '.')
    safe = path.replace(BACKSLASH, '/').strip() if path else '.'
    if safe.startswith('/') or (len(safe) > 1 and safe[1] == ':'):
        return {'success': False, 'error': 'path 不合法'}
    if '..' in safe.split('/'):
        return {'success': False, 'error': 'path 不合法'}
    # v0.36.1: 路径自动补全
    _resolved, _resolve_err, _candidates = _resolve_path(safe)
    if _resolve_err:
        if _candidates and len(_candidates) > 1:
            return {'success': False, 'error': _resolve_err, 'candidates': _candidates}
        return {'success': False, 'error': _resolve_err}
    if _resolved != safe:
        print(f'[grep_code] path "{safe}" 未找到，自动解析为 "{_resolved}"')
        safe = _resolved
    file_ext = params.get('file_ext', '').strip()
    if file_ext and not file_ext.startswith('.'):
        file_ext = '.' + file_ext
    max_results = int(params.get('max_results', 30))
    if max_results < 1 or max_results > 100:
        max_results = 30
    context_lines = int(params.get('context_lines', 0))
    if context_lines < 0:
        context_lines = 0
    if context_lines > 10:
        context_lines = 10
    try:
        _regex = re.compile(pattern)
    except re.error:
        _regex = None
    matches = []
    scanned = 0
    for full, rel in _iter_files(REPO_ROOT, safe, file_ext):
        scanned += 1
        if scanned > 2000:
            break
        try:
            _size = os.path.getsize(full)
            if context_lines > 0 and _size <= MAX_FILE_BYTES:
                # 有上下文：一次性读入内存
                with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                    _lines = f.readlines()
                for i, line in enumerate(_lines):
                    _matched = (_regex.search(line) is not None) if _regex else (pattern in line)
                    if _matched:
                        _ln = i + 1
                        _start = max(0, i - context_lines)
                        _end = min(len(_lines), i + context_lines + 1)
                        _ctx = ''.join(
                            f"{j+1}: {_lines[j].rstrip()}\n" for j in range(_start, _end)
                        ).rstrip('\n')
                        matches.append({
                            'file': rel,
                            'line': _ln,
                            'text': line.rstrip()[:200],
                            'context': _ctx,
                        })
                        if len(matches) >= max_results:
                            break
            else:
                # 无上下文或文件过大：逐行迭代
                with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                    for ln, line in enumerate(f, 1):
                        _matched = (_regex.search(line) is not None) if _regex else (pattern in line)
                        if _matched:
                            matches.append({'file': rel, 'line': ln, 'text': line.rstrip()[:200]})
                            if len(matches) >= max_results:
                                break
        except Exception:
            continue
        if len(matches) >= max_results:
            break
    _result = {'success': True, 'pattern': pattern, 'scanned_files': scanned, 'count': len(matches), 'matches': matches}
    if context_lines > 0:
        _result['context_lines'] = context_lines
    return _result