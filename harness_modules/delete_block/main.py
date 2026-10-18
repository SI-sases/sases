import json
import os
import shutil
import ast

ALLOWED = ('static/', 'core/', 'scripts/', 'docs/', 'harness_modules/', 'launcher/', 'data/')


def _resolve(path):
    p = path.replace('\\', '/')
    if os.path.isabs(p):
        return p
    return os.path.join(os.getcwd(), p)


def _check_allowed(path):
    p = path.replace('\\', '/')
    if os.path.isabs(p):
        return True
    return any(p.startswith(a) for a in ALLOWED)


def _find_block(lines, start_pattern):
    start = -1
    for i, ln in enumerate(lines):
        if start_pattern in ln:
            start = i
            break
    if start < 0:
        return None, '未找到 start_pattern'
    depth = 0
    seen = False
    end = -1
    for i in range(start, len(lines)):
        for ch in lines[i]:
            if ch == '{':
                depth += 1
                seen = True
            elif ch == '}':
                depth -= 1
        if seen and depth <= 0:
            end = i
            break
    if end < 0:
        return None, '括号未闭合，未找到代码块结尾'
    return (start, end), None


def _orphan_check(lines, start, end):
    lo = max(0, start - 5)
    hi = min(len(lines), end + 6)
    bad = []
    for i in range(lo, hi):
        if start <= i <= end:
            continue
        s = lines[i].strip()
        for kw in ('try {', 'catch', 'for (', 'for(', 'if (', 'if('):
            if s.startswith(kw):
                bad.append('行%d: %s' % (i + 1, s[:60]))
    return bad


def run(params):
    file_path = params.get('file_path', '')
    start_pattern = params.get('start_pattern', '')
    end_marker = params.get('end_marker', '')
    replace_with = params.get('replace_with', '')
    if not file_path or not start_pattern:
        return {'ok': False, 'error': '缺少 file_path 或 start_pattern'}
    if not _check_allowed(file_path):
        return {'ok': False, 'error': '路径不在允许目录内'}
    fp = _resolve(file_path)
    if not os.path.exists(fp):
        return {'ok': False, 'error': '文件不存在: ' + file_path}
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    rng, err = _find_block(lines, start_pattern)
    if err:
        return {'ok': False, 'error': err}
    start, end = rng
    if end_marker and end_marker not in lines[end]:
        return {'ok': False, 'error': '结束行不含 end_marker，疑似定位错误: ' + lines[end].strip()[:60]}
    bad = _orphan_check(lines, start, end)
    if bad:
        return {'ok': False, 'error': '检测到孤立控制块，已中止', 'detail': bad}
    backup = fp + '.bak'
    shutil.copyfile(fp, backup)
    new_lines = lines[:start] + ([replace_with] if replace_with else []) + lines[end + 1:]
    new_content = '\n'.join(new_lines)
    if fp.endswith('.py'):
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return {'ok': False, 'error': '删除后语法错误，已回滚: %s' % e}
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return {'ok': True, 'deleted_lines': [start + 1, end + 1], 'backup': backup}
