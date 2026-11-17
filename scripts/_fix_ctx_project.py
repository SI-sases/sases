# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

p = Path('core/services/supervisor/context.py')
s = p.read_text(encoding='utf-8')

if "startswith('sases_api_')" in s:
    print('ALREADY_DONE')
    exit(0)

old = "        _allow_project = bool(supervisor_id) and supervisor_id.startswith('sases_assistant')"
new = "        _allow_project = bool(supervisor_id) and (supervisor_id.startswith('sases_assistant') or supervisor_id.startswith('sases_api_'))"

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
