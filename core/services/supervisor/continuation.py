import json
from datetime import datetime
from ...db import db_cursor
from .. import credit_service
from .constants import MAX_ROUNDS, CREDITS_PER_ROUND, USE_STRUCTURED_REVIEW
from .runs import get_run, finish_run, record_round, deduct_round
from .decider import decide_next_step, task_summarizer, build_next_input

def signal_restart(run_id, reason=''):
    try:
        import time
        content = f"run_id={run_id}|reason={reason}|at={int(time.time())}"
        import os as _os_r
        _root = _os_r.path.dirname(_os_r.path.dirname(_os_r.path.dirname(_os_r.path.dirname(_os_r.path.abspath(__file__)))))
        _fp = _os_r.path.join(_root, 'restart_signal.txt')
        with open(_fp, 'w', encoding='utf-8') as f:
            f.write(content)
        print('[supervisor] restart signal written to ' + _fp + ' content=' + content)
        return True
    except Exception as e:
        print(f"[supervisor] signal_restart failed: {e}")
        return False


async def resume_restart_pending_runs():
    import asyncio
    await asyncio.sleep(10)
    try:
        from .. import swarm_service
        with db_cursor() as cur:
            cur.execute("SELECT id, conversation_id, user_id, goal, supervisor_id, history FROM supervisor_runs WHERE status='restart_pending' ORDER BY id DESC LIMIT 5")
            rows = [dict(r) for r in cur.fetchall()]
        if not rows:
            return
        for row in rows:
            _rid = row['id']
            # 检查最后一轮 review 是否已达成目标，已达成则直接 completed
            try:
                _hist_r = json.loads(row.get('history') or '[]')
                _last_rev = _hist_r[-1].get('review') if _hist_r else None
                if _last_rev and isinstance(_last_rev, dict) and _last_rev.get('goal_achieved') is True:
                    with db_cursor(commit=True) as _cur_done:
                        _cur_done.execute("UPDATE supervisor_runs SET status='completed' WHERE id=?", (_rid,))
                    print('[supervisor] resume: run ' + str(_rid) + ' 目标已达成，直接 completed')
                    continue
            except Exception as _e_hist:
                print('[supervisor] resume 检查历史失败: ' + str(_e_hist))
            # 续跑：改成 running_resumed，继续 plan_task
            # handle_step_done 检测到 running_resumed 会跳过 restart_pending 判断，防止死循环
            with db_cursor(commit=True) as cur2:
                cur2.execute("UPDATE supervisor_runs SET status='running_resumed' WHERE id=?", (_rid,))
            _goal = (row.get('goal') or '')[:300]
            _text = '继续未完成的任务。原目标：' + _goal + '。已完成的部分不要重复，请继续做剩余部分。'
            print('[supervisor] resume: run ' + str(_rid) + ' 标记 running_resumed，继续执行')
            try:
                await swarm_service.plan_task(
                    user_id=row['user_id'],
                    conversation_id=row['conversation_id'],
                    user_input=_text,
                    supervisor_id=row.get('supervisor_id'),
                    supervisor_run_id=_rid,
                )
            except Exception as e:
                print('[supervisor] resume run ' + str(_rid) + ' failed: ' + str(e))
    except Exception as e:
        print('[supervisor] resume_restart_pending_runs failed: ' + str(e))




async def check_and_continue(run_id, last_summary, plan_text=None, exec_text=None, review=None):
    import openai
    from ... import config
    run = get_run(run_id)
    if not run or run['status'] != 'running':
        return False, None

    # 死循环检测：连续 3 轮 plan 高度相似 → 强制停止
    try:
        import difflib as _dl
        _hist = json.loads(run['history'] or '[]')
        if len(_hist) >= 3:
            _p1 = (_hist[-1].get('plan') or '')[:200]
            _p2 = (_hist[-2].get('plan') or '')[:200]
            _p3 = (_hist[-3].get('plan') or '')[:200]
            if _p1 and _p2 and _p3:
                _s12 = _dl.SequenceMatcher(None, _p1, _p2).ratio()
                _s23 = _dl.SequenceMatcher(None, _p2, _p3).ratio()
                if _s12 >= 0.9 and _s23 >= 0.9:
                    print('[supervisor] 检测到死循环（连续3轮相似度 ' + str(round(_s12, 2)) + '/' + str(round(_s23, 2)) + '），强制停止')
                    finish_run(run_id, 'loop_detected')
                    return False, None
    except Exception as _le:
        print('[supervisor] 死循环检测异常: ' + str(_le))

    # v0.18.3: no_progress check with plan similarity
    try:
        import difflib as _dl2
        _hist_check = json.loads(run['history'] or '[]')
        if len(_hist_check) >= 5:
            _recent5 = _hist_check[-5:]
            _any_patch = False
            for _h in _recent5:
                _etxt = str(_h.get('exec', ''))
                if '[success] file_patch' in _etxt or '[success] run_python' in _etxt or '[success] verify_patch' in _etxt:
                    _any_patch = True
                    break
            if not _any_patch:
                _plans = [(h.get('plan') or '')[:200] for h in _recent5]
                _similar = False
                for _i in range(len(_plans) - 1):
                    if _plans[_i] and _plans[_i+1]:
                        _sr = _dl2.SequenceMatcher(None, _plans[_i], _plans[_i+1]).ratio()
                        if _sr >= 0.85:
                            _similar = True
                            break
                if _similar:
                    print('[supervisor] no_progress stop')
                    finish_run(run_id, 'no_progress')
                    return False, None
    except Exception as _pe:
        print('[supervisor] check failed: ' + str(_pe))

    record_round(run_id, plan_text or run.get('goal', ''), exec_text or last_summary, review=review)
    run = get_run(run_id)
    if not run or (run['current_round'] or 0) >= (run['max_rounds'] or 5):
        return False, None
    if (run['credits_used'] or 0) >= 16:
        print('[supervisor] 成本达到 16 积分，提前停止')
        finish_run(run_id, 'budget_exceeded')
        return False, None

    if not deduct_round(run_id):
        finish_run(run_id, status='insufficient_credits')
        return False, None
    return True, build_next_input(run_id)
