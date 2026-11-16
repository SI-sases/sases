# -*- coding: utf-8 -*-
"""彻底清除 file_patch 内存缓存"""
from pathlib import Path
import py_compile

changed = False

# 1. harness_loader.py：跳过 _disabled_ 开头目录
p1 = Path('core/harness_loader.py')
s1 = p1.read_text(encoding='utf-8')
if 'startswith("_disabled_")' not in s1 and "startswith('_disabled_')" not in s1:
    old = '''        module_dir = os.path.join(modules_dir, module_id)
        if not os.path.isdir(module_dir):
            continue'''
    new = '''        module_dir = os.path.join(modules_dir, module_id)
        if not os.path.isdir(module_dir):
            continue
        if module_id.startswith('_disabled_'):
            continue'''
    if old in s1:
        s1 = s1.replace(old, new, 1)
        p1.write_text(s1, encoding='utf-8')
        changed = True
        print('[1] loader 跳过 _disabled_ 目录')
    else:
        print('[1] LOADER_ANCHOR_NOT_FOUND')
else:
    print('[1] ALREADY_DONE')

# 2. harness_runtime.py：invoke_tool 排除 file_patch
p2 = Path('core/harness_runtime.py')
s2 = p2.read_text(encoding='utf-8')
if "_DISABLED_IDS" not in s2:
    old = '''        info = self._modules.get(module_id)
        if not info:'''
    new = '''        _DISABLED_IDS = {'file_patch', 'edit_file'}
        if module_id in _DISABLED_IDS:
            return ToolInvokeResponse(
                success=False,
                module_id=module_id,
                error='file_patch 已废弃，请用 file_write / smart_edit / file_replace_range',
                duration_ms=0,
            )

        info = self._modules.get(module_id)
        if not info:'''
    if old in s2:
        s2 = s2.replace(old, new, 1)
        p2.write_text(s2, encoding='utf-8')
        changed = True
        print('[2] invoke_tool 排除 file_patch/edit_file')
    else:
        print('[2] RUNTIME_ANCHOR_NOT_FOUND')
else:
    print('[2] ALREADY_DONE')

# 3. 语法校验
for f in [p1, p2]:
    try:
        py_compile.compile(str(f), doraise=True)
        print('[SYNTAX_OK]', f.name)
    except Exception as e:
        print('[SYNTAX_ERROR]', f.name, e)
        exit(1)
