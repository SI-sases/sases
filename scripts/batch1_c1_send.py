# -*- coding: utf-8 -*-
"""C1-send: send.py 加 human_summary 辅助函数 + 两处推送"""
F = "core/services/message/send.py"
c = open(F, encoding="utf-8").read()

MARK = "def _build_human_summary("
if MARK in c:
    print("[SKIP] C1-send 已存在")
    exit(0)

# 1. 加辅助函数（插到 send_message 函数定义之前）
HELPER = '''
def _build_human_summary(plan_result, user_input):
    """C1: 组装三段式。LLM 有 human_summary 就用，否则从 steps 兜底"""
    if not plan_result or not isinstance(plan_result, dict):
        return ''
    if plan_result.get('human_summary'):
        return str(plan_result['human_summary'])
    steps = plan_result.get('steps') or []
    if not steps:
        return ''
    descs = []
    for s in steps[:8]:
        d = s.get('description') or s.get('command') or s.get('module_id') or ''
        if d:
            descs.append('- ' + str(d)[:120])
    files = set()
    for s in steps:
        p = (s.get('params') or {}).get('file_path') if isinstance(s.get('params'), dict) else None
        if p:
            files.add(p)
    out = '【分析】\\n'
    out += '- 你的指令：' + str(user_input)[:100] + '\\n'
    out += '- 已拆解为 ' + str(len(steps)) + ' 步\\n'
    if files:
        out += '- 涉及文件：' + ', '.join(list(files)[:5]) + '\\n'
    out += '\\n【方案】\\n' + '\\n'.join(descs) + '\\n'
    out += '\\n【建议】\\n'
    out += '- 执行完成后我汇报结果\\n'
    out += '- 中途失败可以说"继续"或"换方案"\\n'
    return out


'''

ANCHOR1 = "async def send_message("
if ANCHOR1 not in c:
    print("[ERR] send_message 锚点未找到")
    exit(1)
c = c.replace(ANCHOR1, HELPER + ANCHOR1, 1)

# 2. L617 分支：在 # v0.37.0 之前推 human_summary
ANCHOR2 = "                        # v0.37.0: plan_task 返回 None 或 no_plan/error 时立即结束 run，避免卡死会话锁"
PUSH_BLOCK = '''                        # C1: 派单前推 human_summary
                        if _plan_result and _plan_result.get('status') == 'planned':
                            try:
                                _hs = _build_human_summary(_plan_result, content)
                                if _hs:
                                    from .swarm.helpers import _insert_message as _im_hs
                                    _im_hs(_cid_auto, _hs, sender_agent_id=sender_agent_id or agent_id)
                            except Exception as _e_hs:
                                print("[C1] human_summary 推送失败: " + str(_e_hs))
                        # v0.37.0: plan_task 返回 None 或 no_plan/error 时立即结束 run，避免卡死会话锁'''

if ANCHOR2 not in c:
    print("[ERR] L640 锚点未找到")
    exit(1)
c = c.replace(ANCHOR2, PUSH_BLOCK, 1)

# 3. L1194 分支：reply 赋值后加 human_summary 覆盖
ANCHOR3 = '''                else:
                    reply = "执行失败，请重试。"

                return {
                    "conversation_id": conversation_id,
                    "user_message": content,
                    "assistant_reply": reply,'''
NEW3 = '''                else:
                    reply = "执行失败，请重试。"
                # C1: 用 human_summary 覆盖 reply
                try:
                    _hs2 = _build_human_summary(plan_result, content)
                    if _hs2:
                        reply = _hs2
                except Exception as _e_hs2:
                    print("[C1] human_summary 兜底失败: " + str(_e_hs2))

                return {
                    "conversation_id": conversation_id,
                    "user_message": content,
                    "assistant_reply": reply,'''

if ANCHOR3 not in c:
    print("[ERR] L1222 return 锚点未找到")
    exit(1)
c = c.replace(ANCHOR3, NEW3, 1)

open(F, "w", encoding="utf-8").write(c)
import ast
ast.parse(c)
print("[OK] C1-send 已改：辅助函数 + L617 推送 + L1194 覆盖")
print("[INFO] 文件大小:", len(c))