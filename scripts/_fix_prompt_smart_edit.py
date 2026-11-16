# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

p = Path('core/services/swarm/prompts.py')
s = p.read_text(encoding='utf-8')

if '行内子串' in s:
    print('ALREADY_DONE')
    exit(0)

# 在【前提验证铁律】第 5 条后加一条
old = '''   - 用户说"改成"是"修改现有值"，不是"创建新变量"'''

new = '''   - 用户说"改成"是"修改现有值"，不是"创建新变量"
   - 【工具选择】X 是行内子串时，必须用 smart_edit(old_code=X, new_code=Y)；只有 X 占满整行时才用 file_replace_range，禁止用 file_replace_range 替换行内子串（会丢掉原行其它内容）'''

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
