import ast
import json
import re
import shutil
import subprocess
import os
from datetime import datetime


def _backup(path):
    bak_dir = os.path.join(os.path.dirname(path) or '.', '.backups')
    os.makedirs(bak_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    bak = os.path.join(bak_dir, os.path.basename(path) + '.' + ts + '.bak')
    shutil.copy2(path, bak)
    return bak


def _syntax_check(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.py':
            with open(path, 'r', encoding='utf-8') as f:
                ast.parse(f.read())
            return True, ''
        if ext == '.js':
            r = subprocess.run(['node', '--check', path], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return True, ''
            return False, (r.stderr or r.stdout)[:500]
    except Exception as e:
        return False, str(e)
    return True, ''


def _similar(lines, pattern):
    best = None
    best_score = 0
    key = pattern.strip()
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s:
            continue
        score = 0
        for ch in key:
            if ch in s:
                score += 1
        if score > best_score:
            best_score = score
            best = (i, s)
    return best


def delete_block(file_path, start_pattern, end_marker, replace_with='// 代码块已删除'):
    if not os.path.isfile(file_path):
        return {'ok': False, 'error': '文件不存在: ' + file_path}
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if start_pattern in ln]
    if not starts:
        sim = _similar(lines, start_pattern)
        hint = ('最相似: 行 %d: %s' % sim) if sim else '无相似行'
        return {'ok': False, 'error': '未找到 start_pattern', 'hint': hint}
    if len(starts) > 1:
        return {'ok': False, 'error': 'start_pattern 匹配到 %d 行，请提供更精确的模式' % len(starts), 'lines': [i + 1 for i in starts]}
    s = starts[0]
    if end_marker in lines[s]:
        e = s
    else:
        e = None
        for j in range(s + 1, len(lines)):
            if end_marker in lines[j]:
                e = j
                break
        if e is None:
            return {'ok': False, 'error': '从起始行往下未找到 end_marker: ' + end_marker}
    bak = _backup(file_path)
    new_lines = lines[:s] + [replace_with + '\n'] + lines[e + 1:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(''.join(new_lines))
    ok, err = _syntax_check(file_path)
    if not ok:
        shutil.copy2(bak, file_path)
        return {'ok': False, 'error': '语法检查失败，已回滚', 'detail': err, 'backup': bak}
    return {'ok': True, 'deleted_lines': e - s + 1, 'start_line': s + 1, 'end_line': e + 1, 'syntax_ok': True, 'backup': bak}


TOOL_SPEC = {
    'name': 'delete_block',
    'description': '安全删除多行代码块（自动备份+语法检查+失败回滚）',
    'parameters': {
        'type': 'object',
        'properties': {
            'file_path': {'type': 'string', 'description': '文件路径'},
            'start_pattern': {'type': 'string', 'description': '代码块起始特征'},
            'end_marker': {'type': 'string', 'description': '代码块结束标记'},
            'replace_with': {'type': 'string', 'description': '替换注释，默认 // 代码块已删除'}
        },
        'required': ['file_path', 'start_pattern', 'end_marker']
    }
}


def run(file_path, start_pattern, end_marker, replace_with='// 代码块已删除'):
    return delete_block(file_path, start_pattern, end_marker, replace_with)
