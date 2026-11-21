# -*- coding: utf-8 -*-
"""diag_all: 一次查完全部前端菜单+后端接口要的信息"""
import os, glob, sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))

def sec(t):
    print('\n' + '='*70)
    print(t)
    print('='*70)

def dump_func(fpath, func_patterns, max_lines=50):
    """打印包含函数的段落"""
    if not os.path.exists(fpath):
        print(f'[NOT FOUND] {fpath}')
        return
    c = open(fpath, encoding='utf-8').read()
    lines = c.split('\n')
    for pat in func_patterns:
        for i, line in enumerate(lines, 1):
            if pat in line:
                print(f'\n--- {fpath}:{i} ({pat}) ---')
                end = min(i + max_lines, len(lines))
                for j in range(i-1, end):
                    print(f'{j+1}: {lines[j].rstrip()[:180]}')
                break

# [1] chat.js 里 import 的菜单模块
sec('[1] chat.js imports（看哪个菜单文件生效）')
p = os.path.join(ROOT, 'static/modules/chat.js')
if os.path.exists(p):
    for i, line in enumerate(open(p, encoding='utf-8').read().split('\n'), 1):
        s = line.strip()
        if s.startswith('import ') or 'from ' in s and './' in s:
            print(f'{i}: {s[:180]}')

# [2] 两个菜单文件的完整 HTML 生成段
sec('[2] chat_menu.js 长按菜单 HTML（145-200 行）')
p = os.path.join(ROOT, 'static/modules/chat_menu.js')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    for j in range(144, min(200, len(lines))):
        print(f'{j+1}: {lines[j].rstrip()[:200]}')

sec('[2b] message_actions.js 完整内容（前 80 行）')
p = os.path.join(ROOT, 'static/modules/message_actions.js')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    print(f'总行数: {len(lines)}')
    for j in range(0, min(80, len(lines))):
        print(f'{j+1}: {lines[j].rstrip()[:200]}')
else:
    print('[NOT FOUND]')

# [3] 帮我回复的完整实现（两个文件都看）
sec('[3a] chat_menu.js reply 处理（160-230 行）')
p = os.path.join(ROOT, 'static/modules/chat_menu.js')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    for j in range(159, min(230, len(lines))):
        print(f'{j+1}: {lines[j].rstrip()[:200]}')

sec('[3b] message_actions.js reply 处理（20-80 行）')
p = os.path.join(ROOT, 'static/modules/message_actions.js')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    for j in range(19, min(80, len(lines))):
        print(f'{j+1}: {lines[j].rstrip()[:200]}')

# [4] chat.js 里有没有帮我的辅助函数（抓上下文）
sec('[4] chat.js 里 reply/assist/help 相关函数')
p = os.path.join(ROOT, 'static/modules/chat.js')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if any(k in s for k in ['window.assist', 'window.help', 'window.ask',
                                 'replyForMessage', 'replyCurrent', 'assistReply',
                                 'getRecentContext', '_getMsgContext']):
            print(f'{i}: {s[:180]}')

# [5] 消息元素有没有 data-message-id（删除功能依赖）
sec('[5] chat_ui.js / chat.js 里 data-message-id')
for f in ['static/modules/chat_ui.js', 'static/modules/chat.js']:
    p = os.path.join(ROOT, f)
    if not os.path.exists(p): continue
    lines = open(p, encoding='utf-8').read().split('\n')
    for i, line in enumerate(lines, 1):
        if 'data-message-id' in line or 'dataset.messageId' in line:
            print(f'{f}:{i}: {line.strip()[:180]}')

# [6] 后端消息删除接口
sec('[6] 后端消息删除接口（grep message_routes / chat_routes）')
for f in glob.glob(os.path.join(ROOT, 'core/api_routes/*.py')):
    c = open(f, encoding='utf-8').read()
    for i, line in enumerate(c.split('\n'), 1):
        if ('delete' in line.lower() and 'message' in line.lower()) or \
           ('message' in line.lower() and '@router.delete' in line.lower()):
            print(f'{os.path.basename(f)}:{i}: {line.strip()[:180]}')

# [7] send.py 里草稿前缀识别的完整段（560-700 行）
sec('[7] send.py 草稿前缀处理（560-700 行）')
p = os.path.join(ROOT, 'core/services/message/send.py')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    for j in range(559, min(700, len(lines))):
        s = lines[j]
        if '草稿' in s or 'require_confirmation' in s or 'is_draft' in s or '#1' in s or '#4' in s:
            print(f'{j+1}: {s.rstrip()[:200]}')

# [8] intent_service 里 is_task_intent_with_history 完整实现
sec('[8] is_task_intent_with_history 完整实现（210-260 行）')
p = os.path.join(ROOT, 'core/services/intent_service.py')
if os.path.exists(p):
    lines = open(p, encoding='utf-8').read().split('\n')
    for j in range(209, min(280, len(lines))):
        print(f'{j+1}: {lines[j].rstrip()[:200]}')

print('\n' + '='*70)
print('诊断完成')
print('='*70)
