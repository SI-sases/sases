# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

p = Path('harness_modules/file_write/main.py')
s = p.read_text(encoding='utf-8')

if 'new_content' in s and 'allow_empty' in s:
    print('ALREADY_DONE')
    exit(0)

# 1. 兼容 new_content/text，空内容报错
old = '''def run(params):
    _content = params.get("content") or params.get("text") or ""'''
new = '''def run(params):
    _content = params.get("content") or params.get("new_content") or params.get("text") or ""
    if not _content and not params.get("allow_empty"):
        return {"success": False, "error": "content 为空，拒绝写入空文件。如确需空文件请传 allow_empty=true"}'''
if old in s:
    s = s.replace(old, new, 1)
    print('[1] 兼容 new_content + 空内容报错')
else:
    print('[1] OLD_NOT_FOUND')

# 2. 第 43 行 content 用 _content，避免再读一次丢数据
old = '''    file_path = params.get("file_path", "")
    content = params.get("content", "")'''
new = '''    file_path = params.get("file_path", "")
    content = _content'''
if old in s:
    s = s.replace(old, new, 1)
    print('[2] content 统一用 _content')
else:
    print('[2] OLD_NOT_FOUND')

p.write_text(s, encoding='utf-8')

try:
    py_compile.compile(str(p), doraise=True)
    print('SYNTAX_OK')
except Exception as e:
    print('SYNTAX_ERROR', e)
    exit(1)
