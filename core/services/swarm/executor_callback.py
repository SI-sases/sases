
# FORCE_RETRY_CHECK
def _force_retry_if_not_achieved(run_id, review):
    if isinstance(review, dict) and review.get('goal_achieved') is False:
        print('[supervisor] FORCE_RETRY: 任务未完成，强制触发下一轮')
        from .runs import get_run, finish_run
        run = get_run(run_id)
        if run and run['status'] == 'running':
            # 不改状态，直接在外部调度
            pass
import json
from datetime import datetime
from typing import Optional, Dict, Any
from .. import memory_service
from .memory_cache import _pending
from .persistence import _save_pending, _delete_pending_from_db, _load_pending, _log_review
from .reviewer import review_step
from .task_state import _save_task_state
from .summarizer import _summarize, _summary_sender
from .commander import plan_task, replan_failed_steps
from .helpers import _insert_message


def _push_script_output(conversation_id, task):
    """推送 task results 的脚本实际输出（restart_pending 场景用）"""
    try:
        _raw = ''
        for _r in (task.get('results', []) if isinstance(task, dict) else []):
            _o = str(_r.get('output') or '')
            if _o.strip():
                _raw += _o + chr(10)
        if _raw.strip():
            _insert_message(conversation_id, '[SUMMARY]:' + _raw[:3000], sender_agent_id=_summary_sender(task))
            print('[swarm] restart_pending 输出推送: ' + str(len(_raw)) + ' 字符')
    except Exception as _e_po:
        print('[swarm] restart_pending 输出推送失败: ' + str(_e_po))

async def handle_step_done(
    conversation_id: int,
    payload: Dict[str, Any],
    executor_id: str
) -> Optional[Dict[str, Any]]:
    _is_resumed_chk = False
    _run_id = None
    task_id = payload.get("task_id")
    step_id = payload.get("step")
    if not task_id:
        return None

    if task_id not in _pending:
        task = _load_pending(task_id)
        if task:
            _pending[task_id] = task
        else:
            return None

    task = _pending[task_id]
    _run_id = task.get("supervisor_run_id")

    if task.get("cancelled"):
        del _pending[task_id]
        _delete_pending_from_db(task_id)
        return {"status": "cancelled", "task_id": task_id}

    original_step = None
    for s in task["steps"]:
        if s.get("step") == step_id:
            original_step = s
            break
    if original_step is None:
        original_step = {"step": step_id, "command": ""}

    status = payload.get("status", "unknown")
    output = payload.get("output", "")
    review_result, review_reason = review_step(original_step, status, output)

    task["done"].add(step_id)
    task["results"].append({
        "step": step_id,
        "description": payload.get("description", ""),
        "command": original_step.get("command", "") or original_step.get("module_id", ""),
        "status": status,
        "review": review_result,
        "reason": review_reason,
        "output": (output or "")[:12000],
    })
    _save_pending(task)

    print(f"[swarm] step {step_id} 审核: {review_result} | {review_reason}")

    if review_result == "retry":
        try:
            fail_cmd = original_step.get("command", "") or original_step.get("module_id", "")
            fail_content = (
                f"命令「{fail_cmd[:150]}」执行失败。\n"
                f"失败原因：{review_reason}"
            )
            memory_service.remember(
                user_id=task["user_id"],
                memory_type="failure_pattern",
                content=fail_content,
                task_id=task_id,
                importance=0.5,
                tags="failure,swarm"
            )
            print(f"[swarm] 失败记忆已写入")
        except Exception as e:
            print(f"[swarm] 写失败记忆失败: {e}")

    try:
        _log_review(
            task_id=task_id,
            conversation_id=conversation_id,
            step_id=step_id,
            command=original_step.get("command", "") or original_step.get("module_id", ""),
                step_type="command" if original_step.get("command") else "harness",
            exec_status=status,
            review_result=review_result,
            review_reason=review_reason,
            output=output
        )
    except Exception as e:
        print(f"[swarm] 审核日志入库失败: {e}")

    _unique_step_ids = set(str(s.get("step")) for s in task["steps"])
    _unique_done_ids = set(str(d) for d in task["done"])
    if len(_unique_done_ids) >= len(_unique_step_ids):
        failed = [r for r in task["results"] if r.get("review") == "retry"]
        blocked = [r for r in task["results"] if r.get("status") == "blocked"]

        if blocked:
            print(f"[swarm] 发现 {len(blocked)} 个被拒绝的命令，跳过重拆")
            summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
            _insert_message(conversation_id, f"[SUMMARY]:{summary}", sender_agent_id=_summary_sender(task))
            del _pending[task_id]
            _delete_pending_from_db(task_id)
            _run_id = task.get("supervisor_run_id")
            # answer tool output => finish directly
            from .. import supervisor_service as _sv_a
            _has_answer = any(
                (r.get('module_id') == 'answer' or r.get('command') == 'answer')
                and r.get('status') == 'success'
                for r in task['results']
            )
            if _has_answer:
                # v0.19: answer 也需 task_summarizer 判断目标是否真达成
                _ans_ok = True
                if getattr(_sv_a, 'USE_STRUCTURED_REVIEW', False):
                    try:
                        _ans_rev = await _sv_a.task_summarizer(task)
                        if _ans_rev and not _ans_rev.get('goal_achieved'):
                            _ans_ok = False
                            print('[supervisor] answer 产出但目标未达成，强制发起下一轮')
                            if not task.get("_script_fallback_tried"):
                                task["_script_fallback_tried"] = True
                                print("[swarm] 触发强制兜底，尝试生成上下文脚本")
                                try:
                                    from .commander import generate_script_for_task
                                    _script_fb = await generate_script_for_task(
                                        task["user_id"], conversation_id, task["user_text"], task["results"]
                                    )
                                    if _script_fb:
                                        task["steps"] = [{"step": 1, "type": "harness", "module_id": "run_python", "params": {"code": _script_fb}}]
                                        task["results"] = []
                                        task["done"] = set()
                                        task["retry_count"] = 0
                                        _save_pending(task)
                                        _insert_message(conversation_id, "[SUPERVISOR_PROGRESS]:任务卡住，已降级为脚本模式", sender_agent_id=task.get("commander_id"))
                                        print("[swarm] 自动兜底成功，构造 run_python")
                                        return {"status": "script_fallback", "task_id": task_id}
                                except Exception as _e_sf:
                                    print("[swarm] 自动兜底异常: " + str(_e_sf))
                            _next_task = '[MODIFY] ' + (_ans_rev.get('next_hint') or '继续完成目标')
                            await plan_task(
                                user_id=task["user_id"],
                                conversation_id=conversation_id,
                                user_input=task["user_text"] + chr(10) + _next_task,
                                supervisor_id=task.get("supervisor_id"),
                                supervisor_run_id=_run_id,
                            )
                            return {"status": "continue", "task_id": task_id}
                        else:
                            _sv_a.record_round(_run_id, plan_summary='', exec_summary='', review=_ans_rev) if _run_id else None
                    except Exception as _ae:
                        print('[supervisor] answer review 失败: ' + str(_ae))
                if _ans_ok:
                    print('[supervisor] run ' + str(_run_id) + ' completed')
                    _sv_a.finish_run(_run_id, 'completed')
                    return {"status": "completed", "task_id": task_id, "summary": "answer 工具产出"}
                # else fall through 到续轮逻辑

            if _run_id:
                # v0.18.1: 单步任务全成功 -> 直接完成，不续轮
                _is_simple = (len(task.get('steps', [])) == 1 and len(task.get('results', [])) == 1 and all(r.get('review') != 'retry' for r in task.get('results', [])))
                _s1_chk = task.get('steps', [{}])[0] if task.get('steps') else {}
                _s1_mod = _s1_chk.get('module_id', '') or ''
                _s1_type = _s1_chk.get('type', 'command')
                _is_hands_on = (_s1_type == 'harness' and _s1_mod in ('file_patch', 'run_python', 'verify_patch'))
                if not _is_hands_on:
                    _is_simple = False
                # 改 core/ 时标记 restart_pending（优先于 _is_simple 直接返回）
                # 修复 v2：用 command 字段判断（results 里 module_id 被合并进 command）
                if _run_id:
                    try:
                        _has_core = False
                        for _r in task['results']:
                            _r_status = str(_r.get('status') or '')
                            _r_cmd = str(_r.get('command') or '')
                            _desc = str(_r.get('description') or '')
                            _out = str(_r.get('output') or '')
                            if _r_status != 'success':
                                continue
                            if _r_cmd != 'file_patch':
                                continue
                            if 'core/' in _desc or 'core/' in _out or 'core\\' in _desc or 'core\\' in _out:
                                _has_core = True
                                break
                        # running_resumed 状态下跳过 restart_pending（防止续跑死循环）
                        _is_resumed_chk = False
                        try:
                            from .. import supervisor_service as _sv_chk
                            _run_row_chk = _sv_chk.get_run(_run_id)
                            if _run_row_chk and _run_row_chk.get('status') == 'running_resumed':
                                _is_resumed_chk = True
                                print(f"[supervisor] run {_run_id} 处于 running_resumed，跳过 restart_pending")
                        except Exception:
                            pass
                        if _has_core and not _is_resumed_chk:
                            from .. import supervisor_service as _sv_pre
                            try:
                                _steps_txt = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                                _exec_txt = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                                _sv_pre.record_round(
                                    _run_id,
                                    plan_summary=_steps_txt,
                                    exec_summary=_exec_txt,
                                    review={'goal_achieved': True, 'goal_reason': '改动完成，仅需重启验证', 'missing': [], 'next_hint': ''},
                                )
                            except Exception as _e_rec3:
                                print(f"[supervisor] record_round (pre-restart) 失败: {_e_rec3}")
                            _push_script_output(conversation_id, task)
                            _sv_pre.finish_run(_run_id, 'restart_pending')
                            print(f"[supervisor] run {_run_id} 标记 restart_pending（改了 core/，需重启验证）")
                            _sv_pre.signal_restart(_run_id, 'restart_pending')
                            return {'status': 'restart_pending', 'task_id': task_id}
                    except Exception as _e_pre:
                        print(f"[supervisor] pre-restart 失败: {_e_pre}")
                if _is_simple:
                    from .. import supervisor_service as _sv_done
                    _sv_done.finish_run(_run_id, 'completed')
                    print(f"[supervisor] run {_run_id} 单步任务成功，直接完成")
                    return {'status': 'completed', 'task_id': task_id, 'summary': summary}
                try:
                    from .. import supervisor_service
                    _steps_text = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                    _exec_text = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                    _has_core_change = False
                    try:
                        for _r in task['results']:
                            _cmd = str(_r.get('command') or '')
                            _desc = str(_r.get('description') or '')
                            _params = str(_r.get('params') or '')
                            if _cmd == 'file_patch' and ('core/' in _desc or 'core/' in _params or 'core/' in str(_r.get('output') or '')):
                                _has_core_change = True
                                break
                    except Exception:
                        pass
                    if _has_core_change and not _is_resumed_chk:
                        # 先写一条"已完成"的 review，避免 resume 时误判为未完成
                        try:
                            supervisor_service.record_round(
                                _run_id,
                                plan_summary=_steps_text,
                                exec_summary=_exec_text,
                                review={'goal_achieved': True, 'goal_reason': '改动完成，仅需重启验证', 'missing': [], 'next_hint': ''},
                            )
                        except Exception as _e_rec2:
                            print(f"[supervisor] record_round (restart_pending) 失败: {_e_rec2}")
                        try:
                            _push_script_output(conversation_id, task)
                            supervisor_service.finish_run(_run_id, 'restart_pending')
                            print(f"[supervisor] run {_run_id} 标记 restart_pending（改了 core/，需重启验证）")
                            try:
                                supervisor_service.signal_restart(_run_id, 'restart_pending')
                            except Exception as _se:
                                print(f"[supervisor] signal_restart 失败: {_se}")
                        except Exception as _e:
                            print(f"[supervisor] 标记 restart_pending 失败: {_e}")
                        return {"status": "restart_pending", "task_id": task_id}
                    _review = None
                    if getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                        _review = await supervisor_service.task_summarizer(task)
                    # 每轮写入 history，供 resume 时判断是否已达成目标
                    if _run_id and _review:
                        try:
                            supervisor_service.record_round(
                                _run_id,
                                plan_summary=_steps_text,
                                exec_summary=_exec_text,
                                review=_review,
                            )
                        except Exception as _e_rec:
                            print(f"[supervisor] record_round 失败: {_e_rec}")
                    _continue, _ = await supervisor_service.check_and_continue(_run_id, summary, plan_text=_steps_text, exec_text=_exec_text, review=_review)
                    
                    # 强制拦截：如果总结器判定未完成，无视 _continue 的返回值，直接强制续轮
                    if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:
                        _force_retry_count = task.get('_force_retry_count', 0)
                        if _force_retry_count < 2:
                            task['_force_retry_count'] = _force_retry_count + 1
                            _continue = True
                            print(f'[supervisor] FORCE_RETRY: 判定未完成，强制覆盖为 True 进入下一轮（第 {_force_retry_count + 1} 次）')
                        else:
                            print('[supervisor] FORCE_RETRY 已达上限（2次），强制终止任务并报错')
                            supervisor_service.finish_run(_run_id, 'max_force_retry_exceeded')
                            return {"status": "failed", "task_id": task_id, "summary": "由于代码修改连续失败，任务已被强制终止，以防止无意义死循环。"}

                    if _continue:
                        if _review and getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                            if _review.get('goal_achieved'):
                                _decision = {'action': 'done'}
                            else:
                                _ans_wait_text = ''
                                for _r_w in task.get('results', []):
                                    if (_r_w.get('module_id') == 'answer' or _r_w.get('command') == 'answer') and _r_w.get('status') == 'success':
                                        _ans_wait_text += str(_r_w.get('output') or '') + ' ' + str(_r_w.get('answer') or '')
                                _wait_kw = ['请提供', '请说明', '请告诉', '请确认', '需要你', '请补', '请先', '请给']
                                if _ans_wait_text and any(_k in _ans_wait_text for _k in _wait_kw):
                                    _decision = {'action': 'waiting_user'}
                                else:
                                    _decision = {'action': 'execute', 'task': '[MODIFY] ' + (_review.get('next_hint') or '继续完成目标')}
                        else:
                            _decision = await supervisor_service.decide_next_step(_run_id)
                        if _decision and _decision.get("action") == "waiting_user":
                            supervisor_service.finish_run(_run_id, "waiting_user")
                            print(f"[supervisor] run {_run_id} 等待用户输入，已放锁")
                        elif _decision and _decision.get("action") == "done":
                            supervisor_service.finish_run(_run_id, "completed")
                            print(f"[supervisor] run {_run_id} 已完成（调度者判定）")
                        elif _decision and _decision.get("task"):
                            print(f"[supervisor] run {_run_id} 继续下一轮（blocked）：{_decision.get('action')}")
                            _insert_message(conversation_id, '[SUPERVISOR_PROGRESS]:🧠 第 ' + str((task.get('current_round') or 0) + 1) + ' 轮', sender_agent_id=_summary_sender(task))
                            _next_result = await plan_task(
                                user_id=task["user_id"],
                                conversation_id=conversation_id,
                                user_input=task["user_text"] + chr(10) + '[MODIFY] ' + _decision["task"],
                                supervisor_id=task.get("supervisor_id"),
                                supervisor_run_id=_run_id,
                            )
                            if isinstance(_next_result, dict) and _next_result.get("status") == "done":
                                supervisor_service.finish_run(_run_id, "completed")
                            elif _next_result is None or (isinstance(_next_result, dict) and _next_result.get("status") in ("no_plan", "error")):
                                print(f"[supervisor] run {_run_id} 续跑 plan_task 失败: {(_next_result or {}).get('reason', _next_result) if isinstance(_next_result, dict) else _next_result}")
                                supervisor_service.finish_run(_run_id, "plan_failed")
                        else:
                            supervisor_service.finish_run(_run_id, "completed")
                    else:
                        supervisor_service.finish_run(_run_id, "completed")
                except Exception as e:
                    print(f"[supervisor] 续轮失败: {e}")
                    try:
                        supervisor_service.finish_run(_run_id, "error")
                    except Exception:
                        pass
            return {"status": "completed_with_blocks", "task_id": task_id}

        if failed and task["retry_count"] < 2:
            task["retry_count"] += 1
            print(f"[swarm] 发现 {len(failed)} 个失败步骤，触发重拆 (第 {task['retry_count']} 次)")

            # 重拆前先检查：已成功的步骤里是否有 core/ 改动
            _core_before_replan = False
            try:
                for _r in task["results"]:
                    _st = str(_r.get('status') or '')
                    _cmd = str(_r.get('command') or '')
                    _desc = str(_r.get('description') or '')
                    _out = str(_r.get('output') or '')
                    if _st == 'success' and _cmd == 'file_patch' and ('core/' in _desc or 'core/' in _out):
                        _core_before_replan = True
                        break
            except Exception:
                pass
            if _core_before_replan and not _is_resumed_chk:
                # 先写一条"已完成"的 review，避免 resume 时误判为未完成
                from .. import supervisor_service as _sv_replan
                try:
                    _steps_txt_re = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                    _exec_txt_re = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                    _sv_replan.record_round(
                        _run_id,
                        plan_summary=_steps_txt_re,
                        exec_summary=_exec_txt_re,
                        review={'goal_achieved': True, 'goal_reason': '改动完成，仅需重启验证', 'missing': [], 'next_hint': ''},
                    )
                except Exception as _e_rec4:
                    print(f"[supervisor] record_round (replan) 失败: {_e_rec4}")
                try:
                    _push_script_output(conversation_id, task)
                    _sv_replan.finish_run(_run_id, 'restart_pending')
                    print(f"[supervisor] run {_run_id} 重拆前发现 core/ 改动，优先触发 restart_pending")
                    try:
                        _sv_replan.signal_restart(_run_id, 'restart_pending')
                    except Exception as _se:
                        print(f"[supervisor] signal_restart 失败: {_se}")
                except Exception as _e:
                    print(f"[supervisor] 标记 restart_pending 失败: {_e}")
                return {"status": "restart_pending", "task_id": task_id}

            new_steps = await replan_failed_steps(task)

            if new_steps:
                task["results"] = []
                task["done"] = set()
                task["steps"] = new_steps
                _save_pending(task)

                retry_payload = {"task_id": task_id, "steps": new_steps}
                retry_msg = "[RETRY_TASK]:" + json.dumps(retry_payload, ensure_ascii=False)
                _insert_message(conversation_id, retry_msg, sender_agent_id=task["commander_id"])

                return {
                    "status": "retry_triggered",
                    "task_id": task_id,
                    "new_steps": new_steps,
                    "retry_count": task["retry_count"]
                }
            else:
                print(f"[swarm] 重拆失败或跳过，直接汇总")
                summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
                _insert_message(conversation_id, f"[SUMMARY]:{summary}", sender_agent_id=_summary_sender(task))
                del _pending[task_id]
                _delete_pending_from_db(task_id)
                return {"status": "completed_with_failures", "task_id": task_id}
        else:
            if failed and not task.get("_script_fallback_tried"):
                task["_script_fallback_tried"] = True
                print("[swarm] 重拆已达上限，尝试降级为脚本模式")
                _script_fb = None
                try:
                    from .commander import generate_script_for_task
                    _script_fb = await generate_script_for_task(
                        task["user_id"], conversation_id, task["user_text"], failed
                    )
                except Exception as _e_sf:
                    print("[swarm] 脚本降级异常: " + str(_e_sf))
                if _script_fb:
                    task["steps"] = [{"step": 1, "type": "harness", "module_id": "run_python", "params": {"code": _script_fb}}]
                    task["results"] = []
                    task["done"] = set()
                    task["retry_count"] = 0
                    _save_pending(task)
                    _insert_message(conversation_id, "[SUPERVISOR_PROGRESS]:降级为脚本模式", sender_agent_id=task.get("commander_id"))
                    print("[swarm] 脚本降级成功，已构造单步 run_python task")
                    return {"status": "script_fallback", "task_id": task_id}
                print("[swarm] 脚本降级失败，强制结束任务，防止死循环")
                _insert_message(conversation_id, "[SUMMARY]:❌ 任务执行失败。AI连续重试且无法生成兜底脚本，已强制终止。", sender_agent_id=_summary_sender(task))
                del _pending[task_id]
                _delete_pending_from_db(task_id)
                return {"status": "failed", "task_id": task_id}
            if failed:
                print(f"[swarm] 重试次数已达上限，标记失败并汇总")
            else:
                try:
                    steps_desc = "\n".join(
                        f"  {r['step']}. {r.get('command', '')[:80]}"
                        for r in task["results"]
                    )
                    success_content = (
                        f"任务「{task['user_text']}」成功完成。\n"
                        f"使用命令：\n{steps_desc}"
                    )
                    memory_service.remember(
                        user_id=task["user_id"],
                        memory_type="task_result",
                        content=success_content,
                        task_id=task_id,
                        importance=0.6,
                        tags="success,swarm"
                    )
                    print(f"[swarm] 成功记忆已写入")
                except Exception as e:
                    print(f"[swarm] 写成功记忆失败: {e}")


            summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
            summary = await _summarize(task["user_text"], task["results"], user_id=task["user_id"], task_id=task_id)
            # v0.19: 保存本轮任务状态
            _rid_state = task.get("supervisor_run_id")
            if _rid_state:
                try:
                    import re as _re_st
                    import json as _js_st
                    _facts = []
                    _seen_lines = set()
                    _task_text = str(task.get('user_text') or '')
                    _fn_match = _re_st.findall(r'[\w/\-]+\.\w{1,6}', _task_text)
                    _file_name = _fn_match[0] if _fn_match else ''
                    for _r in task.get("results", []):
                        _out = str(_r.get("output") or "")
                        try:
                            _d = _js_st.loads(_out)
                        except Exception:
                            _d = None
                        if isinstance(_d, dict) and isinstance(_d.get("hits"), list):
                            _fn = _d.get("source_file") or _file_name
                            for _h in _d["hits"]:
                                _ln_num = _h.get("line")
                                if _ln_num and _ln_num not in _seen_lines:
                                    _seen_lines.add(_ln_num)
                                    _facts.append({"file": _fn, "line": _ln_num, "text": str(_h.get("text") or "")[:100]})
                        _out2 = _out.replace('\\n', chr(10))
                        for _m in _re_st.finditer(r'(?m)(\d+):\s+([^\n]{3,120})', _out2):
                            _ln_num = int(_m.group(1))
                            if _ln_num in _seen_lines:
                                continue
                            _seen_lines.add(_ln_num)
                            _facts.append({"file": _file_name, "line": _ln_num, "text": _m.group(2).strip()[:100]})
                    _save_task_state(f"run_{_rid_state}", task.get("user_id"), {
                        "facts": _facts[-15:],
                        "pending": [],
                    })
                    print(f"[state] 已保存快照 run_{_rid_state}，facts={len(_facts)}")
                except Exception as _se:
                    print(f"[state] save failed: {_se}")
            _insert_message(conversation_id, f"[SUMMARY]:{summary}", sender_agent_id=_summary_sender(task))
            del _pending[task_id]
            _delete_pending_from_db(task_id)

            _run_id = task.get("supervisor_run_id")
            # answer tool output => finish directly
            from .. import supervisor_service as _sv_a
            _has_answer = any(
                (r.get('module_id') == 'answer' or r.get('command') == 'answer')
                and r.get('status') == 'success'
                for r in task['results']
            )
            if _has_answer:
                # v0.19: answer 也需 task_summarizer 判断目标是否真达成
                _ans_ok = True
                if getattr(_sv_a, 'USE_STRUCTURED_REVIEW', False):
                    try:
                        _ans_rev = await _sv_a.task_summarizer(task)
                        if _ans_rev and not _ans_rev.get('goal_achieved'):
                            _ans_ok = False
                            print('[supervisor] answer 产出但目标未达成，强制发起下一轮')
                            if not task.get("_script_fallback_tried"):
                                task["_script_fallback_tried"] = True
                                print("[swarm] 触发强制兜底，尝试生成上下文脚本")
                                try:
                                    from .commander import generate_script_for_task
                                    _script_fb = await generate_script_for_task(
                                        task["user_id"], conversation_id, task["user_text"], task["results"]
                                    )
                                    if _script_fb:
                                        task["steps"] = [{"step": 1, "type": "harness", "module_id": "run_python", "params": {"code": _script_fb}}]
                                        task["results"] = []
                                        task["done"] = set()
                                        task["retry_count"] = 0
                                        _save_pending(task)
                                        _insert_message(conversation_id, "[SUPERVISOR_PROGRESS]:任务卡住，已降级为脚本模式", sender_agent_id=task.get("commander_id"))
                                        print("[swarm] 自动兜底成功，构造 run_python")
                                        return {"status": "script_fallback", "task_id": task_id}
                                except Exception as _e_sf:
                                    print("[swarm] 自动兜底异常: " + str(_e_sf))
                            _next_task = '[MODIFY] ' + (_ans_rev.get('next_hint') or '继续完成目标')
                            await plan_task(
                                user_id=task["user_id"],
                                conversation_id=conversation_id,
                                user_input=task["user_text"] + chr(10) + _next_task,
                                supervisor_id=task.get("supervisor_id"),
                                supervisor_run_id=_run_id,
                            )
                            return {"status": "continue", "task_id": task_id}
                        else:
                            _sv_a.record_round(_run_id, plan_summary='', exec_summary='', review=_ans_rev) if _run_id else None
                    except Exception as _ae:
                        print('[supervisor] answer review 失败: ' + str(_ae))
                if _ans_ok:
                    print('[supervisor] run ' + str(_run_id) + ' completed')
                    _sv_a.finish_run(_run_id, 'completed')
                    return {"status": "completed", "task_id": task_id, "summary": "answer 工具产出"}
                # else fall through 到续轮逻辑

            if _run_id:
                # v0.18.1: 单步任务全成功 -> 直接完成，不续轮
                _is_simple = (len(task.get('steps', [])) == 1 and len(task.get('results', [])) == 1 and all(r.get('review') != 'retry' for r in task.get('results', [])))
                _s1_chk = task.get('steps', [{}])[0] if task.get('steps') else {}
                _s1_mod = _s1_chk.get('module_id', '') or ''
                _s1_type = _s1_chk.get('type', 'command')
                _is_hands_on = (_s1_type == 'harness' and _s1_mod in ('file_patch', 'run_python', 'verify_patch'))
                if not _is_hands_on:
                    _is_simple = False
                # 改 core/ 时标记 restart_pending（优先于 _is_simple 直接返回）
                # 修复 v2：用 command 字段判断（results 里 module_id 被合并进 command）
                if _run_id:
                    try:
                        _has_core = False
                        for _r in task['results']:
                            _r_status = str(_r.get('status') or '')
                            _r_cmd = str(_r.get('command') or '')
                            _desc = str(_r.get('description') or '')
                            _out = str(_r.get('output') or '')
                            if _r_status != 'success':
                                continue
                            if _r_cmd != 'file_patch':
                                continue
                            if 'core/' in _desc or 'core/' in _out or 'core\\' in _desc or 'core\\' in _out:
                                _has_core = True
                                break
                        # running_resumed 状态下跳过 restart_pending（防止续跑死循环）
                        _is_resumed_chk = False
                        try:
                            from .. import supervisor_service as _sv_chk
                            _run_row_chk = _sv_chk.get_run(_run_id)
                            if _run_row_chk and _run_row_chk.get('status') == 'running_resumed':
                                _is_resumed_chk = True
                                print(f"[supervisor] run {_run_id} 处于 running_resumed，跳过 restart_pending")
                        except Exception:
                            pass
                        if _has_core and not _is_resumed_chk:
                            from .. import supervisor_service as _sv_pre
                            try:
                                _steps_txt = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                                _exec_txt = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                                _sv_pre.record_round(
                                    _run_id,
                                    plan_summary=_steps_txt,
                                    exec_summary=_exec_txt,
                                    review={'goal_achieved': True, 'goal_reason': '改动完成，仅需重启验证', 'missing': [], 'next_hint': ''},
                                )
                            except Exception as _e_rec3:
                                print(f"[supervisor] record_round (pre-restart) 失败: {_e_rec3}")
                            _push_script_output(conversation_id, task)
                            _sv_pre.finish_run(_run_id, 'restart_pending')
                            print(f"[supervisor] run {_run_id} 标记 restart_pending（改了 core/，需重启验证）")
                            _sv_pre.signal_restart(_run_id, 'restart_pending')
                            return {'status': 'restart_pending', 'task_id': task_id}
                    except Exception as _e_pre:
                        print(f"[supervisor] pre-restart 失败: {_e_pre}")
                if _is_simple:
                    from .. import supervisor_service as _sv_done
                    _sv_done.finish_run(_run_id, 'completed')
                    print(f"[supervisor] run {_run_id} 单步任务成功，直接完成")
                    return {'status': 'completed', 'task_id': task_id, 'summary': summary}
                try:
                    from .. import supervisor_service
                    _steps_text = ' | '.join([str(r.get('step')) + '.' + str(r.get('description', ''))[:40] for r in task['results']])
                    _exec_text = chr(10).join([str(r.get('step')) + '.[' + str(r.get('status', '?')) + '] ' + str(r.get('command') or r.get('module_id') or '')[:80] for r in task['results']])
                    _has_core_change = False
                    try:
                        for _r in task['results']:
                            _cmd = str(_r.get('command') or '')
                            _desc = str(_r.get('description') or '')
                            _params = str(_r.get('params') or '')
                            if _cmd == 'file_patch' and ('core/' in _desc or 'core/' in _params or 'core/' in str(_r.get('output') or '')):
                                _has_core_change = True
                                break
                    except Exception:
                        pass
                    if _has_core_change and not _is_resumed_chk:
                        # 先写一条"已完成"的 review，避免 resume 时误判为未完成
                        try:
                            supervisor_service.record_round(
                                _run_id,
                                plan_summary=_steps_text,
                                exec_summary=_exec_text,
                                review={'goal_achieved': True, 'goal_reason': '改动完成，仅需重启验证', 'missing': [], 'next_hint': ''},
                            )
                        except Exception as _e_rec2:
                            print(f"[supervisor] record_round (restart_pending) 失败: {_e_rec2}")
                        try:
                            _push_script_output(conversation_id, task)
                            supervisor_service.finish_run(_run_id, 'restart_pending')
                            print(f"[supervisor] run {_run_id} 标记 restart_pending（改了 core/，需重启验证）")
                            try:
                                supervisor_service.signal_restart(_run_id, 'restart_pending')
                            except Exception as _se:
                                print(f"[supervisor] signal_restart 失败: {_se}")
                        except Exception as _e:
                            print(f"[supervisor] 标记 restart_pending 失败: {_e}")
                        return {"status": "restart_pending", "task_id": task_id}
                    _review = None
                    if getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                        _review = await supervisor_service.task_summarizer(task)
                    # 每轮写入 history，供 resume 时判断是否已达成目标
                    if _run_id and _review:
                        try:
                            supervisor_service.record_round(
                                _run_id,
                                plan_summary=_steps_text,
                                exec_summary=_exec_text,
                                review=_review,
                            )
                        except Exception as _e_rec:
                            print(f"[supervisor] record_round 失败: {_e_rec}")
                    _continue, _ = await supervisor_service.check_and_continue(_run_id, summary, plan_text=_steps_text, exec_text=_exec_text, review=_review)
                    
                    # 强制拦截：如果总结器判定未完成，无视 _continue 的返回值，直接强制续轮
                    if _review and isinstance(_review, dict) and _review.get('goal_achieved') is False:
                        _force_retry_count = task.get('_force_retry_count', 0)
                        if _force_retry_count < 2:
                            task['_force_retry_count'] = _force_retry_count + 1
                            _continue = True
                            print(f'[supervisor] FORCE_RETRY: 判定未完成，强制覆盖为 True 进入下一轮（第 {_force_retry_count + 1} 次）')
                        else:
                            print('[supervisor] FORCE_RETRY 已达上限（2次），强制终止任务并报错')
                            supervisor_service.finish_run(_run_id, 'max_force_retry_exceeded')
                            return {"status": "failed", "task_id": task_id, "summary": "由于代码修改连续失败，任务已被强制终止，以防止无意义死循环。"}

                    if _continue:
                        if _review and getattr(supervisor_service, 'USE_STRUCTURED_REVIEW', False):
                            if _review.get('goal_achieved'):
                                _decision = {'action': 'done'}
                            else:
                                _ans_wait_text = ''
                                for _r_w in task.get('results', []):
                                    if (_r_w.get('module_id') == 'answer' or _r_w.get('command') == 'answer') and _r_w.get('status') == 'success':
                                        _ans_wait_text += str(_r_w.get('output') or '') + ' ' + str(_r_w.get('answer') or '')
                                _wait_kw = ['请提供', '请说明', '请告诉', '请确认', '需要你', '请补', '请先', '请给']
                                if _ans_wait_text and any(_k in _ans_wait_text for _k in _wait_kw):
                                    _decision = {'action': 'waiting_user'}
                                else:
                                    _decision = {'action': 'execute', 'task': '[MODIFY] ' + (_review.get('next_hint') or '继续完成目标')}
                        else:
                            _decision = await supervisor_service.decide_next_step(_run_id)
                        if _decision and _decision.get("action") == "waiting_user":
                            supervisor_service.finish_run(_run_id, "waiting_user")
                            print(f"[supervisor] run {_run_id} 等待用户输入，已放锁")
                        elif _decision and _decision.get("action") == "done":
                            supervisor_service.finish_run(_run_id, "completed")
                            print(f"[supervisor] run {_run_id} 已完成（调度者判定）")
                        elif _decision and _decision.get("task"):
                            print(f"[supervisor] run {_run_id} 继续下一轮：{_decision.get('action')} - {_decision.get('task', '')[:50]}")
                            _next_result = await plan_task(
                                user_id=task["user_id"],
                                conversation_id=conversation_id,
                                user_input=task["user_text"] + chr(10) + '[MODIFY] ' + _decision["task"],
                                supervisor_id=task.get("supervisor_id"),
                                supervisor_run_id=_run_id,
                            )
                            if isinstance(_next_result, dict) and _next_result.get("status") == "done":
                                supervisor_service.finish_run(_run_id, "completed")
                            elif _next_result is None or (isinstance(_next_result, dict) and _next_result.get("status") in ("no_plan", "error")):
                                print(f"[supervisor] run {_run_id} 续跑 plan_task 失败: {(_next_result or {}).get('reason', _next_result) if isinstance(_next_result, dict) else _next_result}")
                                supervisor_service.finish_run(_run_id, "plan_failed")
                        else:
                            supervisor_service.finish_run(_run_id, "completed")
                    else:
                        supervisor_service.finish_run(_run_id, "completed")
                        print(f"[supervisor] run {_run_id} 已完成（轮次用尽）")
                except Exception as e:
                    print(f"[supervisor] 续轮失败: {e}")
                    try:
                        supervisor_service.finish_run(_run_id, "error")
                    except Exception:
                        pass

            return {"status": "completed", "task_id": task_id, "summary": summary}

    return {
        "status": "in_progress",
        "task_id": task_id,
        "done": len(task["done"]),
        "total": len(task["steps"]),
        "review": review_result,
    }
