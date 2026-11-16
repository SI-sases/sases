# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

L = '\u201c'
R = '\u201d'
NL = '\n'

p = Path('core/services/swarm/prompts.py')
s = p.read_text(encoding='utf-8')
changes = []

# A3: 删【强制原子化操作】
old = (
    NL + NL +
    '【强制原子化操作】' + NL +
    '1. 你单次执行的任务，如果涉及 2 个或以上的文件修改，必须立刻停止，回复' + L + '任务过大，请指定先改哪一个文件' + R + '。' + NL +
    '2. 如果同一个文件要改 3 处以上，必须立刻停止，回复' + L + '单文件修改点过多，请分批次执行' + R + '。' + NL
)
if old in s:
    s = s.replace(old, NL, 1)
    changes.append('A3 删强制原子化')
else:
    print('[A3] NOT_MATCH')

# A4: 删【最终结案标准】
old = (
    NL + NL +
    '【最终结案标准】' + NL +
    '如果你的任务描述中包含' + L + '修改' + R + '、' + L + '实现' + R + '、' + L + '增加' + R + '等动词，但你在执行历史中没有任何 写文件工具或 run_python 的实际写操作，系统将判定你的任务完全失败！你必须立刻调用工具进行修改，不准只输出代码位置。' + NL
)
if old in s:
    s = s.replace(old, NL, 1)
    changes.append('A4 删最终结案标准')
else:
    print('[A4] NOT_MATCH')

# A5: 删【物理凭证铁律】
old = (
    NL + NL +
    '【物理凭证铁律】' + NL +
    '在任何总结回复中，如果你没有看到 写文件工具 工具返回 "success": true 的凭证，绝对禁止输出' + L + '修改成功' + R + '。你必须如实汇报' + L + '任务失败，原因是工具报错' + R + '，不准编造结果。' + NL
)
if old in s:
    s = s.replace(old, NL, 1)
    changes.append('A5 删物理凭证铁律')
else:
    print('[A5] NOT_MATCH')

if changes:
    p.write_text(s, encoding='utf-8')
    print('CHANGES: ' + ', '.join(changes))
else:
    print('NO_CHANGES')

try:
    py_compile.compile(str(p), doraise=True)
    print('SYNTAX_OK')
except Exception as e:
    print('SYNTAX_ERROR', e)
