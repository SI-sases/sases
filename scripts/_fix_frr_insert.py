# -*- coding: utf-8 -*-
"""修 file_replace_range insert 模式：参考相邻行缩进"""
from pathlib import Path
import py_compile

p = Path('harness_modules/file_replace_range/main.py')
s = p.read_text(encoding='utf-8')

if '_insert_indent' in s:
    print('ALREADY_DONE')
    exit(0)

old = '''    nc = new_content
    if not is_insert and start_line <= total and nc:
        _old_line = lines[start_line - 1]
        _old_indent = _old_line[:len(_old_line) - len(_old_line.lstrip())]
        if not nc.startswith(_old_indent):
            nc = _old_indent + nc.lstrip()
    if nc and not nc.endswith(chr(10)):
        nc = nc + chr(10)
    new_lines = before + ([nc] if nc else []) + after'''

new = '''    nc = new_content
    _insert_indent = ''
    if is_insert and nc:
        _ref_idx = start_line - 1
        if _ref_idx >= len(lines) and total > 0:
            _ref_idx = total - 1
        if 0 <= _ref_idx < len(lines):
            _ref_line = lines[_ref_idx]
            _insert_indent = _ref_line[:len(_ref_line) - len(_ref_line.lstrip())]
        if _insert_indent and not nc.startswith(_insert_indent):
            nc = _insert_indent + nc.lstrip()
    elif not is_insert and start_line <= total and nc:
        _old_line = lines[start_line - 1]
        _old_indent = _old_line[:len(_old_line) - len(_old_line.lstrip())]
        if not nc.startswith(_old_indent):
            nc = _old_indent + nc.lstrip()
    if nc and not nc.endswith(chr(10)):
        nc = nc + chr(10)
    new_lines = before + ([nc] if nc else []) + after'''

if old not in s:
    print('OLD_NOT_FOUND')
    exit(1)

s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('PATCHED')

try:
    py_compile.compile(str(p), doraise=True)
    print('SYNTAX_OK')
except Exception as e:
    print('SYNTAX_ERROR', e)
