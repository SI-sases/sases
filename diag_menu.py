# -*- coding: utf-8 -*-
"""diag_menu: 查菜单结构 + 帮我回复实现 + 草稿前缀识别 + intent 判断逻辑"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

def sec(t):
    print('\n' + '='*70)
    print(t)
    print('='*70)

# [1] chat_menu.js 里长按菜单的完整 HTML 生成
sec('[1] chat_menu.js 长按菜单 HTML 生成部分')
p = os.path.join(ROOT, 'static/modules/chat_menu.js')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    lines = c.split('\n')
    print(f'总行数: {len(lines)}')
    # 找 "帮我回复" 或 "引用" 出现的所有位置及上下文
    for i, line in enumerate(lines, 1):
        if '帮我回复' in line or '帮我提问' in line or '帮我执行' in line or '引用' in line or 'context-menu-item' in line:
            print(f'{i}: {line.rstrip()[:200]}')
else:
    print('[NOT FOUND]')

# [2] chat_menu.js 里帮我的函数定义
sec('[2] chat_menu.js 里所有 window.xxx = function 定义')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    for i, line in enumerate(c.split('\n'), 1):
        s = line.strip()
        if s.startswith('window.') and ('= function' in s or '= async' in s):
            print(f'{i}: {s[:180]}')
        elif s.startswith('function ') and any(k in s for k in ['ask', 'reply', 'message', 'quote', 'execute', 'question']):
            print(f'{i}: {s[:180]}')

# [3] chat.js 里"帮我回复"完整实现
sec('[3] chat.js 里"帮我回复"相关函数完整实现')
p = os.path.join(ROOT, 'static/modules/chat.js')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        if 'reply' in line.lower() and ('function' in line or 'window.' in line or 'async' in line):
            print(f'\n--- line {i} ---')
            for j in range(i-1, min(i+35, len(lines))):
                print(f'{j+1}: {lines[j].rstrip()[:180]}')

# [4] send.py 草稿前缀识别
sec('[4] send.py 里"草稿"前缀识别 + require_confirmation')
p = os.path.join(ROOT, 'core/services/message/send.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    for i, line in enumerate(c.split('\n'), 1):
        if '草稿' in line or 'require_confirmation' in line or 'is_draft' in line:
            print(f'{i}: {line.rstrip()[:200]}')

# [5] intent_service 完整函数列表
sec('[5] intent_service.py 所有函数定义')
p = os.path.join(ROOT, 'core/services/intent_service.py')
if os.path.exists(p):
    c = open(p, encoding='utf-8').read()
    lines = c.split('\n')
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith('def ') or s.startswith('async def '):
            print(f'{i}: {s[:180]}')
    # 找 _is_obvious_chat 的实现
    idx = c.find('def _is_obvious_chat')
    if idx >= 0:
        print('\n--- _is_obvious_chat 完整实现 ---')
        sub = c[idx:idx+1500]
        print(sub)
    # 找 LLM 判定的部分
    for kw in ['_llm_judge', 'call_llm', 'is_task', '强判', '正则']:
        idx = c.find(kw)
        if idx >= 0:
            print(f'\n--- "{kw}" 首次出现 ---')
            print(c[max(0,idx-100):idx+300])
            break
