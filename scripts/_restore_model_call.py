# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

p = Path('core/services/message/model_call.py')
lines = p.read_text(encoding='utf-8').split(chr(10))

# 找 "if not model_config:" 后到 "if model_config["model_type"]" 前的行，替换成正确版本
start = None
end = None
for i, l in enumerate(lines):
    if 'if not model_config:' in l:
        start = i
    if start is not None and 'if model_config["model_type"] == "api":' in l:
        end = i
        break

if start is None or end is None:
    print('ANCHOR_NOT_FOUND', start, end)
    exit(1)

new_block = [
    '        if not model_config:',
    '            raise Exception("未找到模型配置，请先在「我的 → 模型管理」绑定 API Key")',
    '',
]
lines = lines[:start+1] + new_block[1:] + lines[end:]
p.write_text(chr(10).join(lines), encoding='utf-8')
print('RESTORED')

try:
    py_compile.compile(str(p), doraise=True)
    print('SYNTAX_OK')
except Exception as e:
    print('SYNTAX_ERROR', e)
