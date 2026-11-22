import base64
import asyncio
import json
import os
import httpx
from datetime import datetime
from typing import Optional
from ...db import db_cursor
from fastapi import HTTPException
from .router import normalize_prefix as _normalize_prefix, should_fast as _should_fast
from .ingest import classify_task_type as _classify_task_type, fallback_conversation_id as _sases_fallback_cid


from .constants import REQUIRE_TASK_CONFIRMATION, COMMAND_PREFIX_MAP, DRAFT_PREFIXES
from .conversations import create_conversation, get_messages, mark_conversation_read
from .model_call import call_model_with_config
from .attachments import _enrich_attachment

def _notify_schedule_created(user_id, task_id, task, cron):
    async def _go():
        try:
            from ...api_routes.ws_routes import broadcast_to_user
            await broadcast_to_user(user_id, {
                "type": "sases_schedule_created",
                "task_id": task_id,
                "name": (task or {}).get("name") or "",
                "cron": cron,
                "next_run_at": (task or {}).get("next_run_at") or "",
                "text": (task or {}).get("task_template") or (task or {}).get("name") or "",
            })
        except Exception as e:
            print("[schedule] ws 通知失败: " + str(e))
    try:
        asyncio.create_task(_go())
    except Exception:
        pass


def _sases_fallback_cid():
    from .ingest import fallback_conversation_id
    return fallback_conversation_id()



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
    out = '【分析】\n'
    out += '- 你的指令：' + str(user_input)[:100] + '\n'
    out += '- 已拆解为 ' + str(len(steps)) + ' 步\n'
    if files:
        out += '- 涉及文件：' + ', '.join(list(files)[:5]) + '\n'
    out += '\n【方案】\n' + '\n'.join(descs) + '\n'
    out += '\n【建议】\n'
    out += '- 执行完成后我汇报结果\n'
    out += '- 中途失败可以说"继续"或"换方案"\n'
    return out


async def send_message(
    user_id: int,
    conversation_id: int,
    agent_id: str,
    content: str,
    sender_agent_id: str = None,
    mode: str = "normal",
    msg_type: str = "standard",
    max_steps: int = None,
    attachments: list = None
, enabled_api_ids=None, enabled_tool_ids=None, enabled_skill_ids=None, agent_mode=None,
      quote_content=None):
    print(f"[MSG_DEBUG] content={content!r} | mode={mode!r} | agent_id={agent_id!r} | msg_type={msg_type}")
    _ai_content = content
    if quote_content:
        _ai_content = "【引用消息】\n" + str(quote_content)[:1000] + "\n\n【用户消息】\n" + str(content)

    # ===== P0-D: 付费墙预检（#1~#4 执行类消息必须通过 license 检查）=====
    import os as _os_p0d
    _P0D_DEV_BYPASS = (_os_p0d.path.exists("enable_free_mode.txt") or _os_p0d.getenv("SASES_DEV_BYPASS_LICENSE") == "1")
    if _P0D_DEV_BYPASS:
        print("[license] DEV BYPASS: 跳过 P0-D 预检")
    elif isinstance(content, str):
        import re as _re_lic
        _pref_check = _normalize_prefix(content)
        if isinstance(_pref_check, str) and _re_lic.match(r'^#[1-4]:', _pref_check):
            try:
                from ...services.license_service import verify_license_json, get_exec_token
            except ImportError:
                from core.services.license_service import verify_license_json, get_exec_token
            _lic_ok, _lic_reason = verify_license_json()
            if not _lic_ok:
                import os as _os_dev
                if _os_dev.path.exists("enable_free_mode.txt") or _os_dev.getenv("SASES_DEV_BYPASS_LICENSE") == "1":
                    print("[license] DEV BYPASS: 跳过本地 license 校验")
                else:
                    raise HTTPException(status_code=403, detail=f"授权未激活: {_lic_reason}")
            try:
                from launcher.hardware import get_hardware_fingerprint
                _fp = get_hardware_fingerprint()
            except Exception:
                _fp = "unknown"
            _tok = get_exec_token(user_id, _fp)
            if not _tok:
                raise HTTPException(status_code=403, detail="云端授权校验失败")
    # ===== P0-D end =====

    _att_str = json.dumps(attachments) if attachments else None

    # 跨账号投递：好友会话的任何消息（文字/图片/文件）都投递
    if conversation_id:
        try:
            with db_cursor() as _c_fc:
                _c_fc.execute('SELECT is_friend_chat FROM conversations WHERE id=?', (conversation_id,))
                _r_fc = _c_fc.fetchone()
            if _r_fc and _r_fc['is_friend_chat'] == 1:
                from .friend_chat import handle_friend_message
                _friend_res = await handle_friend_message(user_id, conversation_id, content, sender_agent_id, msg_type, attachments, _att_str, agent_id, mode)
                if _friend_res is not None:
                    return _friend_res
                # 好友会话只做投递：任务由对方确认后执行，本机不再重复跑一遍
                return {
                    "conversation_id": conversation_id,
                    "user_message": content,
                    "assistant_reply": "",
                    "agent_id": agent_id,
                    "sender_agent_id": sender_agent_id,
                    "mode": mode,
                }
        except Exception as _e_fc:
            print('[message] 好友投递失败: ' + str(_e_fc))

    # UX-1: 意图识别（用户不用写 # 前缀）
    try:
        from .. import intent_service as _intent_svc
        _ir = _intent_svc.route_intent(content)
        print("[intent] " + str(_ir))
        if _ir.get("intent") == "schedule" and not content.lstrip().startswith("#5"):
            _snap = {"apis": enabled_api_ids or [], "tools": enabled_tool_ids or [], "skills": enabled_skill_ids or []}
            if _ir.get("normalized"):
                content = "#5: " + _ir["normalized"]
            elif _ir.get("weekly") and conversation_id:
                from .. import scheduled_task_service
                _wk = _ir["weekly"]
                _cron = "%d %d * * %d" % (_wk["minute"], _wk["hour"], _wk["weekday"])
                _tid = scheduled_task_service.create_task(
                    user_id=user_id, name=_wk["task"][:10], cron_expr=_cron,
                    task_template=_wk["task"], conversation_id=conversation_id,
                    supervisor_id=sender_agent_id or agent_id or "", capsule_snapshot=_snap)
                _t = scheduled_task_service.get_task(_tid)
                try:
                    _notify_schedule_created(user_id, _tid, _t, _cron)
                except Exception:
                    pass
                return {
                    "conversation_id": conversation_id, "user_message": content,
                    "assistant_reply": "✅ 每周任务已创建：%s\n下次执行：%s" % (
                        _wk["task"], str((_t or {}).get("next_run_at") or "")[:16]),
                    "agent_id": agent_id, "sender_agent_id": sender_agent_id, "mode": mode,
                }
        elif (agent_mode or "auto").strip().lower() == "auto" and _ir.get("mode"):
            agent_mode = _ir["mode"]
    except Exception as _e_int:
        print("[intent] 识别失败: " + str(_e_int))

    # A0: 双写 LLM 消息日志
    try:
        from .. import agent_memory as _am0
        if conversation_id:
            _am0.backfill(conversation_id)
            _am0.append(conversation_id, "user", content, run_id=None)
    except Exception as _e_am0:
        print("[agent_memory] 双写失败: " + str(_e_am0))

    _scan_content = _normalize_prefix(content)

    # ===== #5 定时任务解析 =====
    if _scan_content.strip().startswith('#5:') or _scan_content.strip().startswith('#5：'):
        import re
        from .. import scheduled_task_service
        
        _body = _scan_content.strip()[3:].lstrip('：: ')
        _match = re.match(r'每天(\d+)点(?:(\d+)分)?\s+(.+)', _body)
        if _match:
            hour = int(_match.group(1))
            minute = int(_match.group(2)) if _match.group(2) else 0
            template = _match.group(3)
            cron = f"{minute} {hour} * * *"
            
            try:
                _cid = conversation_id
                _sid = sender_agent_id or agent_id
                
                _tid = scheduled_task_service.create_task(
                    user_id=user_id,
                    name=template[:10],
                    cron_expr=cron,
                    task_template=template,
                    conversation_id=_cid,
                    supervisor_id=_sid,
                    capsule_snapshot={
                        "apis": enabled_api_ids or [],
                        "tools": enabled_tool_ids or [],
                        "skills": enabled_skill_ids or [],
                    },
                )
                _task = scheduled_task_service.get_task(_tid)
                try:
                    _notify_schedule_created(user_id, _tid, _task, cron)
                except Exception:
                    pass
                _reply = f"✅ 定时任务已创建！\n任务内容：{template}\n执行时间：每天 {hour:02d}:{minute:02d}\n下次执行：{_task['next_run_at'][:16]}"
            except Exception as _e:
                _reply = f"❌ 定时任务创建失败：{_e}"
        else:
            _reply = "❌ 格式错误。请使用：`#5: 每天5点 整理邮件` 或 `#5: 每天14点30分 备份数据库`"
            
        return {
            'conversation_id': conversation_id,
            'user_message': content,
            'assistant_reply': _reply,
            'agent_id': agent_id,
            'sender_agent_id': sender_agent_id,
            'mode': mode,
        }
    # =======================

    # A2: fast loop 默认入口（任务/普通消息都走，失败回退下面的旧路径）
    if conversation_id and _should_fast(agent_mode, content, enabled_tool_ids):
        try:
            from .. import fast_agent as _fa_early
            _fr_early = await _fa_early.run_fast(
                user_id, conversation_id, content,
                allowed_tool_ids=enabled_tool_ids,
                max_steps=(max_steps if (max_steps and max_steps > 0) else 8),
            )
            _reply_early = (_fr_early.get("content") or "").strip()
            if _reply_early:
                try:
                    from .reply import insert_message as _ins_early
                    _ins_early(conversation_id, _reply_early, msg_type=msg_type,
                               attachments=_att_str, sync_agent=False)
                except Exception as _e_ins:
                    print("[fast] 落库失败: " + str(_e_ins))
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': _reply_early,
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                    'fast_mode': True,
                    'steps': _fr_early.get("steps"),
                }
            print("[fast] 空结果，回退旧路径")
        except Exception as _e_fast:
            print("[fast] 失败: " + str(_e_fast))
            if os.getenv("SASES_LEGACY_EXEC", "0") != "1":
                return {
                    'conversation_id': conversation_id, 'user_message': content,
                    'assistant_reply': '⚠️ 执行失败：' + str(_e_fast),
                    'agent_id': agent_id, 'sender_agent_id': sender_agent_id, 'mode': mode,
                }

    # A3.5: strict 也走同一 loop（失败回退旧四角色）
    if conversation_id and (agent_mode or '').strip().lower() == 'strict' \
            and __import__("os").getenv("SASES_AGENT_LOOP", "1") != "0":
        try:
            from ..supervisor import runs as _runs_s
            from .. import run_service
            _rid_s = run_service.create_run(user_id, conversation_id, "chat", content,
                                            supervisor_id=sender_agent_id or agent_id or "sases_assistant")
            _rs = await run_service.run_once(
                user_id, conversation_id, content, source="chat",
                supervisor_id=sender_agent_id or agent_id or "sases_assistant",
                allowed_tool_ids=enabled_tool_ids,
                max_steps=(max_steps if (max_steps and max_steps > 0) else 8),
                run_id=_rid_s, finish=False, skill_ids=enabled_skill_ids,
            )
            _fr_s = _rs.get("loop") or {}
            if _fr_s.get("status") == "awaiting_approval":
                return {
                    'conversation_id': conversation_id, 'user_message': content,
                    'assistant_reply': '⏸ 等待审批：' + str(_fr_s.get("tool") or ""),
                    'agent_id': agent_id, 'sender_agent_id': sender_agent_id,
                    'mode': mode, 'strict_mode': True, 'awaiting_approval': True,
                }
            _reply_s = (_fr_s.get("content") or "").strip()
            if _reply_s:
                from .reply import insert_message as _ins_s
                _ins_s(conversation_id, _reply_s, msg_type=msg_type, attachments=_att_str,
                       sync_agent=False)
                try:
                    _loop_status = str(_fr_s.get("status") or "")
                    _run_status = "completed" if _loop_status == "ok" else (
                        "failed" if _loop_status in ("max_steps", "verification_failed", "error") else _loop_status)
                    _runs_s.finish_run(_rid_s, _run_status or "completed")
                except Exception:
                    pass
                return {
                    'conversation_id': conversation_id, 'user_message': content,
                    'assistant_reply': _reply_s, 'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id, 'mode': mode,
                    'strict_mode': True, 'steps': _fr_s.get("steps"),
                }
        except Exception as _e_strict_loop:
            print("[strict] loop 失败: " + str(_e_strict_loop))
            if os.getenv("SASES_LEGACY_EXEC", "0") != "1":
                return {
                    'conversation_id': conversation_id, 'user_message': content,
                    'assistant_reply': '⚠️ 执行失败：' + str(_e_strict_loop),
                    'agent_id': agent_id, 'sender_agent_id': sender_agent_id, 'mode': mode,
                }

    # #0 清锁（最先拦截，绕过所有锁检查）
    if isinstance(content, str) and content.strip().startswith('#0'):
        import os
        import threading
        import time
        try:
            from .. import swarm_service as _sw5
            _sw5.clear_conversation_lock(conversation_id)
            with db_cursor(commit=True) as _c5:
                _c5.execute("UPDATE swarm_pending_tasks SET status='cancelled' WHERE status IN ('pending', 'running')")
                _c5.execute("UPDATE supervisor_runs SET status='interrupted' WHERE status IN ('running', 'proposed')")
            _msg = '✅ 已清理所有卡死任务，服务将在 1 秒后自动重启以清空内存锁！'
        except Exception as _e5:
            _msg = '清锁失败: ' + str(_e5)

        # 强制重启
        def _delayed_exit():
            import gc
            time.sleep(1.5)
            gc.collect()  # 强制垃圾回收，关闭未释放的数据库连接
            os._exit(0)
        threading.Thread(target=_delayed_exit, daemon=True).start()
        # 1. 清理数据库
        import sqlite3 as _sq5, os as _os5
        try:
            _c5db = _sq5.connect('users.db')
            _cur5 = _c5db.cursor()
            _cur5.execute("UPDATE swarm_pending_tasks SET status='cancelled' WHERE status IN ('pending', 'running')")
            _cur5.execute("UPDATE supervisor_runs SET status='interrupted' WHERE status IN ('running', 'proposed')")
            _c5db.commit()
            _c5db.close()
        except Exception as _e5db:
            print('[清锁] 数据库清理异常: ' + str(_e5db))
        # 2. 强制退出进程以清空内存锁，依赖 run_forever.py 自动重启
        import threading as _th5, time as _tm5
        def _delayed_exit5():
            _tm5.sleep(1)
            _os5._exit(0)
        _th5.Thread(target=_delayed_exit5).start()
        if conversation_id:
            try:
                with db_cursor(commit=True) as _c5:
                    _c5.execute(
                        "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)",
                        (conversation_id, _msg, sender_agent_id or agent_id, msg_type, _att_str)
                    )
                    _c5.execute('UPDATE conversations SET updated_at=? WHERE id=?', (datetime.now().isoformat(), conversation_id))
            except Exception:
                pass
        return {
            'conversation_id': conversation_id,
            'user_message': content,
            'assistant_reply': _msg,
            'agent_id': agent_id,
            'sender_agent_id': sender_agent_id,
            'mode': mode,
            'clear_lock': True
        }

    # *2 管理员广播（对普通用户隐藏）
    if isinstance(_scan_content, str) and _scan_content.strip().startswith('*2:'):
        from ... import auth_service as _auth
        if not _auth.is_admin(user_id):
            # 普通用户拦截，静默替换为普通聊天，不暴露 *2 存在
            _scan_content = content
        
        _bcast_msg = _scan_content.strip()[3:].lstrip('：: ')
        if not _bcast_msg:
            return {
                'conversation_id': conversation_id,
                'user_message': content,
                'assistant_reply': '❌ 广播内容不能为空。',
                'agent_id': agent_id,
                'sender_agent_id': sender_agent_id,
                'mode': mode,
            }
            
        try:
            with db_cursor(commit=True) as _cur_b:
                _cur_b.execute("SELECT id, username FROM users")
                _users = _cur_b.fetchall()
                _count = 0
                import datetime as _dt_mod
                _now = _dt_mod.datetime.now().isoformat()
                
                for _u in _users:
                    _uid = _u['id']
                    if _uid == user_id:
                        continue
                    
                    _target_agent = f"sases_assistant_{_uid}"
                    _cur_b.execute("SELECT id FROM conversations WHERE user_id=? AND agent_id=?", (_uid, _target_agent))
                    _conv_row = _cur_b.fetchone()
                    
                    if _conv_row:
                        _cid = _conv_row['id']
                    else:
                        _cur_b.execute("INSERT INTO conversations (user_id, agent_id, title) VALUES (?, ?, 'SASES 助手')", (_uid, _target_agent))
                        _cid = _cur_b.lastrowid
                        
                    _cur_b.execute(
                        "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments, created_at) VALUES (?, 'assistant', ?, ?, 'standard', NULL, ?)",
                        (_cid, f"📢 [系统广播] {_bcast_msg}", _target_agent, _now)
                    )
                    _cur_b.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now, _cid))
                    _count += 1
                    
            return {
                'conversation_id': conversation_id,
                'user_message': None, # 管理员界面不展示 *2 指令原文
                'assistant_reply': f'✅ 广播成功，已向 {_count} 个用户发送。',
                'agent_id': agent_id,
                'sender_agent_id': sender_agent_id,
                'mode': mode,
            }
        except Exception as _e_b:
            return {
                'conversation_id': conversation_id,
                'user_message': content,
                'assistant_reply': '❌ 广播发送失败：' + str(_e_b),
                'agent_id': agent_id,
                'sender_agent_id': sender_agent_id,
                'mode': mode,
            }

    # *0 脚本执行（调度员内部能力，用户不可见）
    if isinstance(_scan_content, str) and _scan_content.strip().startswith('*0:'):
        _script_body = _scan_content.strip()
        for _pfx0 in ('*0：', '*0:'):
            if _script_body.startswith(_pfx0):
                _script_body = _script_body[len(_pfx0):].lstrip()
                break
        if not _script_body:
            return {
                'conversation_id': conversation_id,
                'user_message': content,
                'assistant_reply': '脚本为空',
                'agent_id': agent_id,
                'sender_agent_id': sender_agent_id,
                'mode': mode,
            }
        # 自然语言自动转 Python 代码（*0 只接受 Python，非代码内容用 LLM 转换）
        try:
            import ast as _ast0
            _ast0.parse(_script_body)
        except SyntaxError:
            try:
                from ..swarm.llm_parser import _call_llm as _llm0
                _nl_prompt = '把下面的自然语言需求转换成一段完整可执行的 Python 脚本。只输出代码，不要任何解释、不要 markdown 代码块标记。需求：' + _script_body
                _nl_sys = '你是 Python 代码生成器。用户给出自然语言需求，你输出可直接运行的 Python 代码。必须符合 Python 语法，禁止 markdown 代码块标记（禁止 ```），禁止解释文字。'
                _converted = await _llm0(_nl_prompt, system_prompt=_nl_sys, max_tokens=800)
                _converted = _converted.strip()
                if _converted.startswith(chr(96) + chr(96) + chr(96)):
                    _cl = _converted.split(chr(10))
                    if _cl and _cl[0].startswith(chr(96) + chr(96) + chr(96)):
                        _cl = _cl[1:]
                    if _cl and _cl[-1].strip() == chr(96) + chr(96) + chr(96):
                        _cl = _cl[:-1]
                    _converted = chr(10).join(_cl)
                _ast0.parse(_converted)
                _script_body = _converted
            except Exception as _e_nl:
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': '⚠️ 内容既不是合法 Python，也无法自动转换。请提供 Python 代码，或换种描述。原因：' + str(_e_nl)[:150],
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                }
        if len(_script_body) > 50000:
            return {
                'conversation_id': conversation_id,
                'user_message': content,
                'assistant_reply': '脚本过长（上限 50000 字符，当前 ' + str(len(_script_body)) + '）',
                'agent_id': agent_id,
                'sender_agent_id': sender_agent_id,
                'mode': mode,
            }
        try:
            from .. import credit_service as _cs0
            _bal0 = _cs0.get_balance(user_id)
            if _bal0 < 3:
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': '积分不足（需 3 分，当前 ' + str(_bal0) + ' 分）',
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                }
            _cs0.deduct_credits(user_id, 3, '脚本执行', 'script_exec')
        except Exception as _e0:
            return {
                'conversation_id': conversation_id,
                'user_message': content,
                'assistant_reply': '扣分失败: ' + str(_e0),
                'agent_id': agent_id,
                'sender_agent_id': sender_agent_id,
                'mode': mode,
            }
        if not conversation_id:
            conversation_id = create_conversation(user_id, agent_id, '脚本执行')
        import time as _t0
        import secrets as _sec0
        _task_id0 = 'script_' + str(int(_t0.time() * 1000)) + '_' + _sec0.token_hex(3)
        _task0 = {
            'task_id': _task_id0,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'user_text': '[脚本] ' + _script_body[:80],
            'steps': [{'step': 1, 'type': 'harness', 'module_id': 'run_python', 'params': {'code': _script_body}}],
            'results': [],
            'done': set(),
            'commander_id': sender_agent_id or agent_id,
            'executor_id': None,
            'created_at': datetime.now().isoformat(),
            'cancelled': False,
            'no_plan': False,
            'retry_count': 0,
            'is_draft': False,
            'supervisor_id': sender_agent_id or agent_id,
            'supervisor_run_id': locals().get('_supervisor_run_id'),
        }
        from ..swarm.persistence import _save_pending as _sp0
        _sp0(_task0)
        print('[script] *0 task 已创建: ' + _task_id0)
        return {
            'conversation_id': conversation_id,
            'user_message': content,
            'assistant_reply': '⏳ 脚本已提交执行（-3 积分）',
            'agent_id': agent_id,
            'sender_agent_id': sender_agent_id,
            'mode': mode,
            'script_task_id': _task_id0,
        }

    _supervisor_id = sender_agent_id or agent_id
    _raw_content = content if isinstance(content, str) else ''
    # 不切换身份时，若会话默认是 SASES 助手，自动用 agent_id 当发送者
    if not sender_agent_id and agent_id == 'sases_assistant_2':
        sender_agent_id = agent_id

    print(f"[SUPERVISOR_DEBUG] sender_agent_id={sender_agent_id!r} agent_id={agent_id!r} _supervisor_id={_supervisor_id!r}")

    # 兜底：conversation_id 为空时，自动创建（修复对话模式 NOT NULL constraint 失败）
    if not conversation_id:
        _auto_title = "新会话"
        if agent_id:
            with db_cursor() as _cq0:
                _cq0.execute('SELECT name FROM model_configs WHERE id=?', (agent_id,))
                _rq0 = _cq0.fetchone()
            if _rq0:
                _auto_title = _rq0['name']
        conversation_id = create_conversation(user_id, agent_id, _auto_title)
        print(f"[MSG_DEBUG] 兜底创建 conversation_id={conversation_id}")

    # v0.39.0: [CONTENT]: 多段规范化
    if isinstance(content, str) and '[CONTENT]:' in content:
        _parts = content.split('[CONTENT]:')
        if len(_parts) > 2:
            _normalized = _parts[0].rstrip()
            for _ci, _cp in enumerate(_parts[1:], 1):
                _normalized += f"\n\n---\n\n第 {_ci} 段：\n{_cp.strip()}"
            content = _normalized
            print(f"[content] 检测到 {len(_parts)-1} 段 [CONTENT]:，已规范化为 --- 分隔")

    # v0.18.3: 用户输入自动授粉
    try:
        from .. import pollination_service as _poll_in
        _poll_in.try_pollinate_from_input(user_id, conversation_id or 0, content)
    except Exception as _pe:
        print(f'[message] 输入授粉失败: {_pe}')
        
    # 附件消息（[IMAGE]: / [FILE]:）直接入库，不调模型
    _IMG_IMP_E = ('图片导入知识库', '图片存入知识库', '这张图导入知识库', '把图存入知识库')
    _skip_e = any(_k in content for _k in _IMG_IMP_E) if isinstance(content, str) else False
    if isinstance(content, str) and (content.startswith('[IMAGE]:') or content.startswith('[FILE]:')) and not _skip_e:
        if not conversation_id:
            title = '附件'
            if agent_id:
                with db_cursor() as _c:
                    _c.execute('SELECT name FROM model_configs WHERE id=?', (agent_id,))
                    _r = _c.fetchone()
                if _r:
                    title = _r['name']
            conversation_id = create_conversation(user_id, agent_id, title)
        with db_cursor(commit=True) as _c:
            _c.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'user', ?, ?, ?, ?)", (conversation_id, content, sender_agent_id, msg_type, _att_str))
            _c.execute('UPDATE conversations SET updated_at=? WHERE id=?', (datetime.now().isoformat(), conversation_id))


        # 关键改动：把附件内容附加进来，不再 return，继续走正常问答
        try:
            content = _enrich_attachment(content)
        except Exception as _e:
            print('[message] enrich 失败: ' + str(_e))

    # ===== P2-2: 会话级续接（在 #4 判定之前）=====
    if conversation_id and isinstance(content, str):
        _p2_prefixes = ("#1", "#2", "#3", "#4", "草稿", "编辑")
        if not content.strip().startswith(_p2_prefixes):
            try:
                from core.services import intent_service as _is_p2
                from core.services import task_state_service as _ts_p2
                _sess = _is_p2.classify_session_intent(content, conversation_id)
                if _sess in ("resume", "query", "pause", "cancel"):
                    try:
                        _snap = _ts_p2.get_snapshot_fresh(conversation_id) or _ts_p2.get_snapshot(conversation_id)
                    except Exception as _e_fresh:
                        print("[P2-2] get_snapshot_fresh 失败，回退: " + str(_e_fresh))
                        _snap = _ts_p2.get_snapshot(conversation_id)
                    _st = _snap.get("status", "idle")
                    _prog = _snap.get("progress", {})
                    _reply = None

                    if _sess == "cancel":
                        if _st in ("running", "paused", "failed"):
                            try:
                                from core.services.supervisor import runs as _runs_p2
                                from core.db import db_cursor as _dbc_p2
                                with _dbc_p2() as _c_p2:
                                    _c_p2.execute(
                                        "SELECT id FROM supervisor_runs WHERE conversation_id=? AND status IN ('running','paused','failed','awaiting') ORDER BY id DESC LIMIT 1",
                                        (conversation_id,)
                                    )
                                    _r_p2 = _c_p2.fetchone()
                                if _r_p2:
                                    _rid = _r_p2[0] if not isinstance(_r_p2, dict) else _r_p2["id"]
                                    _runs_p2.cancel_run(_rid, user_id)
                                    _ts_p2.finish_task(conversation_id, "cancelled")
                                _reply = "已取消当前任务"
                            except Exception as _e_p2:
                                _reply = "取消失败：" + str(_e_p2)[:80]
                        else:
                            _reply = "当前没有可取消的任务"

                    elif _sess == "pause":
                        if _st == "running":
                            try:
                                from core.services.supervisor import runs as _runs_pause
                                _rid_pause = _snap.get("task_id")
                                _paused_ok = _runs_pause.pause_run(_rid_pause, user_id) if _rid_pause else False
                                if not _paused_ok:
                                    _ts_p2.finish_task(conversation_id, "paused")
                                _reply = "任务已暂停，说'继续'恢复"
                            except Exception as _e_p2:
                                _reply = "暂停失败：" + str(_e_p2)[:80]
                        else:
                            _reply = "当前没有正在运行的任务"

                    elif _sess == "resume":
                        if _st == "running":
                            _run_alive = False
                            try:
                                with db_cursor() as _c_chk:
                                    _c_chk.execute("SELECT status FROM supervisor_runs WHERE id=?", (_snap.get("task_id"),))
                                    _r_chk = _c_chk.fetchone()
                                _st_chk = ((_r_chk["status"] if isinstance(_r_chk, dict) else _r_chk[0]) if _r_chk else None)
                                _run_alive = _st_chk in ("running", "running_resumed", "restart_pending")
                            except Exception as _e_chk:
                                print("[P2-2] resume 校验 run 失败: " + str(_e_chk))
                            if _run_alive:
                                _reply = "任务正在执行中（" + str(_prog.get("completed", 0)) + "/" + str(_prog.get("total", 0)) + "），请稍等"
                            else:
                                try:
                                    _ts_p2.finish_task(conversation_id, "failed")
                                except Exception:
                                    pass
                                _st = "failed"
                                _reply = "任务已终止（run 状态异常），说'重试'重新执行"
                        elif _st == "paused":
                            try:
                                from core.services.supervisor import runs as _runs_resume
                                _rid_resume = _snap.get("task_id")
                                _resumed_ok = _runs_resume.resume_run(_rid_resume, user_id) if _rid_resume else False
                                if not _resumed_ok:
                                    raise RuntimeError("run 不存在或不是 paused")
                                _reply = "已恢复，从第 " + str(_prog.get("current_step", 1)) + " 步继续"
                            except Exception as _e_p2:
                                _reply = "恢复失败：" + str(_e_p2)[:80]
                        elif _st == "failed":
                            _fs = _snap.get("failed_summary") or []
                            _reason = str(_fs[-1].get("reason", ""))[:100] if _fs else "未知"
                            _reply = "上次失败（" + _reason + "）。说'重试'重新执行，或说'取消'放弃"
                        elif _st == "completed":
                            _reply = "上个任务已完成。需要新任务请直接说"
                        else:
                            _reply = "当前没有进行中的任务"

                    elif _sess == "query":
                        _reply = (
                            "当前任务：" + str(_snap.get("goal", ""))
                            + "\n状态：" + str(_st)
                            + "  进度：" + str(_prog.get("completed", 0)) + "/" + str(_prog.get("total", 0))
                        )
                        if _snap.get("current_step_desc"):
                            _reply += "\n当前步骤：" + str(_snap.get("current_step_desc"))
                        _fs = _snap.get("failed_summary") or []
                        if _fs:
                            _reply += "\n最近失败：步骤" + str(_fs[-1].get("step", "")) + " " + str(_fs[-1].get("reason", ""))[:60]

                    if _reply:
                        try:
                            _ts_p2.set_user_intent(conversation_id, _sess, content)
                        except Exception:
                            pass
                        from datetime import datetime as _dt_p2
                        with db_cursor(commit=True) as _c_ins:
                            _c_ins.execute(
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type) VALUES (?, 'user', ?, ?, 'standard')",
                                (conversation_id, content, sender_agent_id)
                            )
                            _c_ins.execute(
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type) VALUES (?, 'assistant', ?, ?, 'standard')",
                                (conversation_id, _reply, sender_agent_id)
                            )
                            _c_ins.execute('UPDATE conversations SET updated_at=? WHERE id=?', (_dt_p2.now().isoformat(), conversation_id))
                        return {
                            "conversation_id": conversation_id,
                            "user_message": content,
                            "assistant_reply": _reply,
                            "agent_id": agent_id,
                            "sender_agent_id": sender_agent_id,
                            "mode": mode,
                        }
            except Exception as _e_p2_outer:
                print("[P2-2] 续接处理失败: " + str(_e_p2_outer))
    # ===== P2-2 end =====

    # ========== 检测草稿前缀 ==========
    require_confirmation = REQUIRE_TASK_CONFIRMATION
    _numbered_prefix_matched = False
    _force_swarm = False
    for _p, _m in COMMAND_PREFIX_MAP.items():
        if _scan_content.startswith(_p):
            _numbered_prefix_matched = True
            content = _scan_content[len(_p):].lstrip()
            if _m == "exec":
                content = "执行：" + content
            elif _m == "task":
                content = "任务：" + content
            elif _m == "draft":
                _force_swarm = True
                require_confirmation = True
            elif _m == "auto":
                try:
                    from .. import supervisor_service
                    existing = supervisor_service.get_active_run(user_id)
                    if existing:
                        return {
                            "conversation_id": conversation_id,
                            "user_message": content,
                            "assistant_reply": "已有运行中的自主任务 (run_id=" + str(existing["id"]) + ")，请先取消或等待完成。",
                            "agent_id": agent_id,
                            "sender_agent_id": sender_agent_id,
                            "mode": mode,
                        }
                    _cid_auto = conversation_id or 0 or _sases_fallback_cid()
                    if not _cid_auto:
                        _title_auto = "自主任务"
                        if agent_id:
                            with db_cursor() as _cq_auto:
                                _cq_auto.execute('SELECT name FROM model_configs WHERE id=?', (agent_id,))
                                _rq_auto = _cq_auto.fetchone()
                            if _rq_auto:
                                _title_auto = _rq_auto['name']
                        _cid_auto = create_conversation(user_id, agent_id, _title_auto)
                        print(f"[supervisor] auto_run 无会话，新建 conversation_id={_cid_auto}")
                    _run_id = supervisor_service.create_run(user_id, _cid_auto, sender_agent_id or agent_id, content, task_type=_classify_task_type(content), max_rounds=max_steps)
                    print("[supervisor] 已创建 run_id=" + str(_run_id) + " goal=" + content[:50])
                    _force_swarm = True
                    _supervisor_run_id = _run_id
                    from .. import swarm_service
                    try:
                        _plan_result = await swarm_service.plan_task(
                            user_id=user_id,
                            conversation_id=_cid_auto,
                            user_input=_ai_content,
                            supervisor_id=sender_agent_id or agent_id,
                            supervisor_run_id=_run_id,
                            enabled_api_ids=enabled_api_ids,
                            enabled_tool_ids=enabled_tool_ids,
                            enabled_skill_ids=enabled_skill_ids,
                        )
                        # v0.38.0: precheck 拦截时，自动重试一次（用 reason 修正 prompt）
                        if _plan_result and isinstance(_plan_result, dict) and _plan_result.get('status') == 'no_plan' and 'precheck blocked' in str(_plan_result.get('reason', '')):
                            print('[supervisor] precheck 拦截，自动重试一次')
                            _retry_input = content + chr(10) + chr(10) + '【上次 precheck 拦截原因，请修正后重新生成】' + chr(10) + str(_plan_result.get('reason', ''))
                            try:
                                _plan_result = await swarm_service.plan_task(
                                    user_id=user_id,
                                    conversation_id=_cid_auto,
                                    user_input=_retry_input,
                                    supervisor_id=sender_agent_id or agent_id,
                                    supervisor_run_id=_run_id,
                            enabled_api_ids=enabled_api_ids,
                            enabled_tool_ids=enabled_tool_ids,
                            enabled_skill_ids=enabled_skill_ids,
                                )
                            except Exception as _e_retry:
                                print('[supervisor] precheck 重试失败: ' + str(_e_retry))
                        # C1: 派单前推 human_summary
                        if _plan_result and _plan_result.get('status') == 'planned':
                            try:
                                _hs = _build_human_summary(_plan_result, content)
                                if _hs:
                                    from .swarm.helpers import _insert_message as _im_hs
                                    _im_hs(_cid_auto, _hs, sender_agent_id=sender_agent_id or agent_id)
                            except Exception as _e_hs:
                                print("[C1] human_summary 推送失败: " + str(_e_hs))
                        # v0.37.0: plan_task 返回 None 或 no_plan/error 时立即结束 run，避免卡死会话锁
                        if _plan_result is None or _plan_result.get('status') in ('no_plan', 'error'):
                            try:
                                supervisor_service.finish_run(_run_id, 'plan_failed')
                            except Exception as _fe:
                                print("[supervisor] auto_run finish_run 失败: " + str(_fe))
                            _fail_reason = '任务拆解失败（precheck 拦截或格式错误）'
                            if _plan_result and _plan_result.get('message'):
                                _fail_reason = _plan_result.get('message')
                            return {
                                'conversation_id': conversation_id,
                                'user_message': content,
                                'assistant_reply': _fail_reason,
                                'agent_id': agent_id,
                                'sender_agent_id': sender_agent_id,
                                'mode': mode,
                                'swarm': False,
                                'swarm_status': 'plan_failed',
                                'task_id': _run_id,
                            }
                        print("[supervisor] auto_run 已派单 run_id=" + str(_run_id))
                    except Exception as _ae:
                        print("[supervisor] auto_run 派单失败: " + str(_ae))
                        try:
                            supervisor_service.finish_run(_run_id, 'plan_failed')
                        except Exception as _fe2:
                            print("[supervisor] auto_run finish_run 异常路径失败: " + str(_fe2))
                    return {
                        'conversation_id': conversation_id,
                        'user_message': content,
                        'assistant_reply': '',
                        'agent_id': agent_id,
                        'sender_agent_id': sender_agent_id,
                        'mode': mode,
                        'swarm': True,
                        'swarm_status': 'auto_run',
                        'task_id': _run_id,
                    }
                except Exception as _e:
                    print("[supervisor] 启动失败: " + str(_e))
                    return {
                        "conversation_id": conversation_id,
                        "user_message": content,
                        "assistant_reply": "自主模式启动失败：" + str(_e),
                        "agent_id": agent_id,
                        "sender_agent_id": sender_agent_id,
                        "mode": mode,
                    }
            break

    for prefix in DRAFT_PREFIXES:
        if content.startswith(prefix):
            require_confirmation = True
            content = content[len(prefix):].strip()
            print(f"[MSG_DEBUG] 检测到草稿前缀，切换为草稿模式")
            break

    # ========== 自然语言意图分流 ==========
    if (
        mode in ("normal", "free")
        and content
        and content.strip()
        and (not content.startswith("[") or content.startswith("[IMAGE]:") or content.startswith("[FILE]:"))
        and not content.startswith("执行：")
    ):
        try:
            from .. import intent_service, swarm_service, project_service
            _OP_VERBS = ('列出', '查看', '打开', '运行', '抓取', '下载', '找到', '查找', '搜索', '读取', '删除', '帮我', '请帮', '分析', '读一下', '看看', '看下')
            _first8 = content.strip()[:8]
            _is_operation = any(_first8.startswith(v) for v in _OP_VERBS)
            _HARNESS_KEYWORDS = ('harness', 'module_id', 'file_patch', 'web_fetch', 'git_ops', 'HARNESS:')
            _is_harness_call = any(kw in content for kw in _HARNESS_KEYWORDS)
            if _is_harness_call:
                _is_operation = True

            _is_greeting = intent_service._is_obvious_chat(content)
            _is_sases_agent = False
            try:
                # 判定用"切换后的身份"，不切换时才用会话默认
                _check_id = sender_agent_id if sender_agent_id else agent_id
                # 只有系统默认助手 sases_assistant_2 才走项目库快答
                if _check_id and _check_id.startswith('sases_assistant'):
                    _is_sases_agent = True
            except Exception:
                pass
            _is_import_intent = (
                any(content.startswith(p) for p in ('导入知识库：','导入知识库:','加入知识库：','加入知识库:','存到知识库：','存到知识库:'))
                or any(_k in content for _k in ('导入知识库','加入知识库','存到知识库','存到项目库','导入项目库','加到知识库'))
            )
            _skip_kb_qa = (
                _scan_content.startswith('*1:')
                or content.startswith('[用户发了一张图片]')
                or content.startswith('[用户发了一个文件')
                or _raw_content.startswith('[IMAGE]:')
                or _raw_content.startswith('[FILE]:')
            )
            if not _skip_kb_qa and not _is_operation and not _numbered_prefix_matched and not _is_greeting and _is_sases_agent and not _is_import_intent:
                try:
                    _chunks = project_service.retrieve_project_chunks(content, top_k=3, user_id=user_id)
                    if _chunks and _chunks[0].get('score', 0) > 0.55:
                        _ctx = project_service.format_chunks_for_prompt(_chunks)
                        _ans_prompt = (_ctx + "\n\n" + content) if _ctx else content
                        if agent_id:
                            with db_cursor() as _cur:
                                _cur.execute('SELECT * FROM model_configs WHERE id=? AND user_id=?', (agent_id, user_id))
                                _mr = _cur.fetchone()
                            if _mr:
                                _mr = dict(_mr)
                                with db_cursor(commit=True) as _cur:
                                    _cur.execute('INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) VALUES (?, ?, ?, ?, ?)', (conversation_id, 'user', content, msg_type, _att_str))
                                try:
                                    _reply = await call_model_with_config(_mr, _ans_prompt)
                                except Exception as _e:
                                    _reply = '模型调用失败: ' + str(_e)
                                with db_cursor(commit=True) as _cur:
                                    _cur.execute('INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) VALUES (?, ?, ?, ?, ?)', (conversation_id, 'assistant', _reply, msg_type, _att_str))
                                    _cur.execute('UPDATE conversations SET updated_at=? WHERE id=?', (datetime.now().isoformat(), conversation_id))
                                print('[message] 项目库快速回答命中，相似度 ' + str(round(_chunks[0].get('score', 0), 3)))
                                return {'conversation_id': conversation_id, 'user_message': content, 'assistant_reply': _reply, 'agent_id': agent_id, 'sender_agent_id': sender_agent_id, 'mode': mode, 'project_kb_hit': True}
                except Exception as _e:
                    print('[message] 项目库快速回答失败: ' + str(_e))

            if _force_swarm:
                is_task = True
            else:
                try:
                    is_task = await intent_service.is_task_intent_with_history(content, conversation_id)
                except NameError:
                    is_task = await intent_service.is_task_intent(content)
            print(f"[MSG_DEBUG] is_task={is_task}")

            # 图片导入知识库
            if _is_sases_agent:
                _img_kw = ("图片导入知识库", "图片存入知识库", "这张图导入知识库", "把图存入知识库")
                if any(_k in _raw_content for _k in _img_kw):
                    if not conversation_id:
                        conversation_id = create_conversation(user_id, agent_id or "sases_assistant_2", "图片导入")
                    try:
                        from .attachments import try_handle_image_import as _try_img
                        _img_reply = _try_img(_raw_content, conversation_id, user_id)
                        if _img_reply:
                            try:
                                with db_cursor(commit=True) as _cwi:
                                    _cwi.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)", (conversation_id, _img_reply, sender_agent_id or agent_id, msg_type, _att_str))
                                    _cwi.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))
                            except Exception as _eiw:
                                print("[message] 图片导入回写失败: " + str(_eiw))
                            return {
                                "conversation_id": conversation_id,
                                "user_message": content,
                                "assistant_reply": _img_reply,
                                "agent_id": agent_id,
                                "sender_agent_id": sender_agent_id or agent_id,
                                "mode": mode,
                                "import_mode": "image"
                            }
                    except Exception as _eii:
                        print("[message] 图片导入异常: " + str(_eii))

            # *1 统一导入（知识库/项目库）
            _uni_text = None
            _uni_target = 'kb'
            if True:
                for _up in ('*1:',):
                    if _scan_content.startswith(_up):
                        _uni_body = _scan_content[len(_up):].strip()
                        if '项目库' in _uni_body.split('\n', 1)[0]:
                            _uni_target = 'project'
                        _uni_lines = _uni_body.split('\n', 1)
                        if len(_uni_lines) > 1:
                            _uni_text = _uni_lines[1].strip()
                            for _skip in ('内容如下', '内容：', '内容:'):
                                if _uni_text.startswith(_skip):
                                    _uni_text = _uni_text[len(_skip):].strip()
                                    break
                        break
            # 单行 *1: 且含图片语义 → 关联最近图片导入
            if not _uni_text and isinstance(content, str) and _scan_content.startswith('*1:'):
                from datetime import datetime as _dtn
                _img_uni_body = content[3:].strip()
                if any(_k in _img_uni_body for _k in ('图片', '这张图', '上图', '刚才的图', '图上的')):
                    _img_rep = ''
                    try:
                        if not conversation_id:
                            conversation_id = create_conversation(user_id, agent_id or 'sases_assistant_2', '图片导入')
                        from .attachments import import_image_to_kb as _imp_img
                        with db_cursor() as _cur_img:
                            _cur_img.execute("SELECT content FROM messages WHERE conversation_id=? AND content LIKE '[IMAGE]:%' ORDER BY id DESC LIMIT 1", (conversation_id,))
                            _row_img = _cur_img.fetchone()
                        if not _row_img:
                            _img_rep = '未找到最近上传的图片，请先发一张图。'
                        else:
                            _img_url = _row_img['content'][8:].split('|')[0].strip()
                            _res_img = _imp_img(_img_url, user_id)
                            if _res_img.get('success'):
                                _img_rep = '✅ 已导入 ' + str(_res_img.get('chunks', 0)) + ' 个分片（' + _res_img.get('source', '') + '）。'
                            else:
                                _img_rep = '❌ 导入失败：' + _res_img.get('error', '未知')
                    except Exception as _e_img:
                        _img_rep = '图片导入异常：' + str(_e_img)
                    try:
                        with db_cursor(commit=True) as _cin_img:
                            _cin_img.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)", (conversation_id, _img_rep, sender_agent_id, msg_type, _att_str))
                            _cin_img.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_dtn.now().isoformat(), conversation_id))
                    except Exception as _e2_img:
                        print('[message] *1 单行图片导入回写失败: ' + str(_e2_img))
                    return {
                        'conversation_id': conversation_id,
                        'user_message': content,
                        'assistant_reply': _img_rep,
                        'agent_id': agent_id,
                        'sender_agent_id': sender_agent_id,
                        'mode': mode,
                        'import_mode': 'image'
                    }
            # 单行 *1: 且非图片 → 提示用户用两行格式
            if not _uni_text and isinstance(content, str) and _scan_content.startswith('*1:'):
                _single_body = _scan_content[3:].strip()
                _hint_body = _single_body
                for _sp in ('导入项目库：', '导入项目库:', '导入项目库', '导入知识库：', '导入知识库:', '导入知识库', '内容如下：', '内容如下', '内容：', '内容:'):
                    if _hint_body.startswith(_sp):
                        _hint_body = _hint_body[len(_sp):].strip()
                        break
                if _hint_body:
                    return {
                        'conversation_id': conversation_id,
                        'user_message': content,
                        'assistant_reply': '📋 知识库导入需要两行格式：' + chr(10) + chr(10) + '第一行：*1: 导入知识库（或 *1: 导入项目库）' + chr(10) + '第二行：要导入的正文内容' + chr(10) + chr(10) + '示例：' + chr(10) + '*1: 导入知识库' + chr(10) + '这是要导入的正文。',
                        'agent_id': agent_id,
                        'sender_agent_id': sender_agent_id,
                        'mode': mode,
                        'import_mode': 'star1_hint'
                    }
            if _uni_text:
                try:
                    from .. import project_service as _ps_uni
                    from ... import auth_service as _auth_uni
                    if _uni_target == 'project' and not _auth_uni.is_admin(user_id):
                        _urep = '❌ 仅管理员可导入项目库'
                    else:
                        _is_proj = (_uni_target == 'project')
                        _usrc = ('管理员导入_' if _is_proj else '对话导入_') + datetime.now().strftime('%Y%m%d_%H%M%S') + '.md'
                        _ps_uni.import_document(_usrc, 'v1.0-admin' if _is_proj else 'v1.0-chat', _uni_text, user_id=0 if _is_proj else user_id, allow_system=_is_proj)
                        with db_cursor() as _ci_uni:
                            _ci_uni.execute("SELECT COUNT(*) as c FROM project_docs_meta WHERE source_file LIKE '对话导入_%' OR source_file LIKE '管理员导入_%'")
                            _un_id = _ci_uni.fetchone()['c']
                        _urep = ('✅ 已导入项目库 *' if _is_proj else '✅ 已导入知识库 *') + str(_un_id) + chr(10) + '内容摘要：' + _uni_text[:80]
                except Exception as _e_uni:
                    _urep = '导入失败：' + str(_e_uni)
                if not conversation_id:
                    conversation_id = create_conversation(user_id, agent_id or 'sases_assistant_2', '导入知识库')
                try:
                    with db_cursor(commit=True) as _cin_uni:
                        _cin_uni.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)", (conversation_id, _urep, sender_agent_id, msg_type, _att_str))
                        _cin_uni.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))
                except Exception as _e2_uni:
                    print('[message] *1 导入回写失败: ' + str(_e2_uni))
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': _urep,
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                    'import_mode': 'star1'
                }

            # 文字导入（"导入知识库：xxx" 格式）
            _INLINE_PREFIXES = ('导入知识库：', '导入知识库:', '加入知识库：', '加入知识库:', '存到知识库：', '存到知识库:')
            _inline_text = None
            if _is_sases_agent:
                for _ip in _INLINE_PREFIXES:
                    if content.startswith(_ip):
                        _inline_text = content[len(_ip):].strip()
                        break
            if _inline_text:
                try:
                    from .. import project_service as _ps_inline
                    _src_inline = '对话导入_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.md'
                    _n_inline = _ps_inline.import_document(_src_inline, 'v1.0-chat', _inline_text, user_id=user_id)
                    _irep_inline = '已导入 ' + str(_n_inline) + ' 个分片（' + _src_inline + '）。'
                except Exception as _e_inline:
                    _irep_inline = '导入失败：' + str(_e_inline)
                if not conversation_id:
                    conversation_id = create_conversation(user_id, agent_id or 'sases_assistant_2', '导入知识库')
                try:
                    with db_cursor(commit=True) as _cin:
                        _cin.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)", (conversation_id, _irep_inline, sender_agent_id, msg_type, _att_str))
                        _cin.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))
                except Exception as _e2_inline:
                    print('[supervisor] 文字导入回写失败: ' + str(_e2_inline))
                return {
                    'conversation_id': conversation_id,
                    'user_message': content,
                    'assistant_reply': _irep_inline,
                    'agent_id': agent_id,
                    'sender_agent_id': sender_agent_id,
                    'mode': mode,
                    'import_mode': 'inline'
                }

            # 导入知识库意图
            _IMPORT_KW = ('导入知识库', '加入知识库', '存到项目库', '导入项目库', '存到知识库', '加到知识库')
            if sender_agent_id and any(_k in content for _k in _IMPORT_KW):
                try:
                    with db_cursor() as _ci:
                        _ci.execute("SELECT content FROM messages WHERE conversation_id=? AND content LIKE '[FILE]:%' ORDER BY id DESC LIMIT 1", (conversation_id,))
                        _fi = _ci.fetchone()
                    if not _fi:
                        _irep = '未找到最近上传的文件，请先上传。'
                    else:
                        _fc = _fi['content'] if 'content' in _fi.keys() else ''
                        _fp = _fc[7:].split('|')
                        _furl = _fp[0] if len(_fp) > 0 else ''
                        _fname = _fp[1] if len(_fp) > 1 else ''
                        from .. import supervisor_service as _svi
                        _ires = _svi.import_file_to_kb(_furl, _fname, user_id)
                        if _ires.get('success'):
                            _irep = '已导入《' + _fname + '》，共 ' + str(_ires.get('chunks', 0)) + ' 个分片。'
                        else:
                            _irep = '导入失败：' + _ires.get('error', '未知')
                    with db_cursor(commit=True) as _cwi:
                        _cwi.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)", (conversation_id, _irep, sender_agent_id, msg_type, _att_str))
                        _cwi.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))
                    return {'conversation_id': conversation_id, 'user_message': content, 'assistant_reply': _irep, 'agent_id': agent_id, 'sender_agent_id': sender_agent_id, 'mode': mode, 'import_mode': True}
                except Exception as _ei:
                    print('[supervisor] 导入失败: ' + str(_ei))

            # 对话模式（v0.18.0）：非任务、非技术指令、非问候，直接回答
            if sender_agent_id and not is_task and not _is_operation and not _is_harness_call and not _is_greeting:
                try:
                    from .. import supervisor_service as _sv
                    _chat_ctx = _sv.build_context(user_id, conversation_id, content, mode='chat', supervisor_id=sender_agent_id)
                    import openai as _coai
                    from ... import config as _ccfg
                    _cclient = _coai.OpenAI(api_key=_ccfg.DEEPSEEK_API_KEY, base_url=_ccfg.DEEPSEEK_BASE_URL, timeout=20)
                    _sys_prompt = '你是 SASES 调度员，正在与用户对话。请直接回答用户（不要提议执行、不要派单），像分析师一样给出判断，最多 200 字。'
                    _user_prompt = '【参考资料】' + chr(10) + _chat_ctx + chr(10) + '【用户说】' + chr(10) + content[:300]
                    _cresp = _cclient.chat.completions.create(model=_ccfg.MODEL_NAME, messages=[{'role': 'system', 'content': _sys_prompt}, {'role': 'user', 'content': _user_prompt}], temperature=0.7, max_tokens=4000)
                    _chat_reply = (_cresp.choices[0].message.content or '').strip()
                    if not _chat_reply:
                        _rc = getattr(_cresp.choices[0].message, 'reasoning_content', None) or ''
                        if _rc:
                            _lines = [l.strip() for l in _rc.split(chr(10)) if l.strip() and not l.strip().startswith(('我们', '需要', '首先', '分析', '但', '然而', '因此', '所以', '根据'))]
                            if _lines:
                                _chat_reply = ' '.join(_lines[-3:])[:300]

                    if _chat_reply:
                        with db_cursor(commit=True) as _ccur:
                            _ccur.execute('SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1', (conversation_id,))
                            _last = _ccur.fetchone()
                            if not (_last and _last[0] == 'user' and _last[1] == content):
                                _ccur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'user', ?, ?, ?, ?)", (conversation_id, content, sender_agent_id, msg_type, _att_str))
                            _ccur.execute(
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, ?, ?, ?, ?, ?)",
                                (conversation_id, 'assistant', _chat_reply, sender_agent_id, msg_type, _att_str)
                            )
                            _ccur.execute(
                                "UPDATE conversations SET updated_at=? WHERE id=?",
                                (datetime.now().isoformat(), conversation_id)
                            )
                        return {
                            'conversation_id': conversation_id,
                            'user_message': content,
                            'assistant_reply': _chat_reply,
                            'agent_id': agent_id,
                            'sender_agent_id': sender_agent_id,
                            'mode': mode,
                            'chat_mode': True
                        }
                except Exception as _che:
                    print('[supervisor] 对话模式失败: ' + str(_che))

            if is_task:
                # [P1-0c-a] 积分拦截：派单前检查，避免消耗 API 后才报积分不足
                try:
                    from .. import credit_service as _cs_gate
                    _need_credit_gate = (
                        _force_swarm
                        or _numbered_prefix_matched
                        or content.strip().startswith(('#1', '#2', '#3', '#4'))
                    )
                    # [P1-0c-a-DEBUG] 打出每个变量的值
                    print(f"[P1-0c-a-DEBUG] _force_swarm={_force_swarm}, _numbered_prefix_matched={_numbered_prefix_matched}, content[:10]={content.strip()[:10]!r}, _need={_need_credit_gate}")
                    if _need_credit_gate:
                        _bal_gate = _cs_gate.get_balance(user_id)
                        print(f"[P1-0c-a-DEBUG] get_balance(user_id={user_id}) = {_bal_gate}")
                        if _bal_gate < 5:
                            print(f"[P1-0c-a] 积分不足拦截: balance={_bal_gate} < 5")
                            _gate_msg = f"\u26a0\ufe0f 积分不足（当前 {_bal_gate}，至少需要 5 积分才能执行指令）。请先充值或等待空投后再试。"
                            with db_cursor(commit=True) as _cur_gate:
                                _cur_gate.execute(
                                    "INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) VALUES (?, 'assistant', ?, 'standard', '[]')",
                                    (conversation_id, _gate_msg)
                                )
                                _cur_gate.execute(
                                    "UPDATE conversations SET updated_at=? WHERE id=?",
                                    (datetime.now().isoformat(), conversation_id)
                                )
                            return {
                                'conversation_id': conversation_id,
                                'user_message': content,
                                'assistant_reply': _gate_msg,
                                'agent_id': agent_id,
                                'sender_agent_id': sender_agent_id,
                                'mode': mode,
                                'credit_gate': True
                            }
                except Exception as _e_gate:
                    print(f"[P1-0c-a] 积分拦截异常（已放行）: {type(_e_gate).__name__}: {_e_gate}")

                from core.services.friend_gate import check_friend_gate
                _gate_res = check_friend_gate(user_id, conversation_id, sender_agent_id, content, agent_id, mode)
                if _gate_res:
                    return _gate_res

                if not conversation_id:
                    title = "蜂群任务"
                    if agent_id:
                        with db_cursor() as cur:
                            cur.execute("SELECT name FROM model_configs WHERE id=?", (agent_id,))
                            row = cur.fetchone()
                            if row:
                                title = row["name"]
                    conversation_id = create_conversation(user_id, agent_id, title)

                # 直达通道：单工具任务不走 swarm（v0.32.0）
                try:
                    from . import direct_channel as _dc
                    if not _numbered_prefix_matched and (agent_mode or '').strip().lower() != 'fast':
                        _dc_ok, _dc_reply = await _dc.try_direct(content, user_id=user_id, conversation_id=conversation_id)
                    else:
                        _dc_ok, _dc_reply = False, ""
                    if _dc_ok:
                        with db_cursor(commit=True) as _cur_dc:
                            _cur_dc.execute(
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)",
                                (conversation_id, _dc_reply, sender_agent_id or 'sases_assistant_2', msg_type, _att_str)
                            )
                            _cur_dc.execute(
                                "UPDATE conversations SET updated_at=? WHERE id=?",
                                (datetime.now().isoformat(), conversation_id)
                            )
                        return {
                            'conversation_id': conversation_id,
                            'user_message': content,
                            'assistant_reply': _dc_reply,
                            'agent_id': agent_id,
                            'sender_agent_id': sender_agent_id,
                            'mode': mode,
                            'direct_channel': True,
                        }
                except Exception as _e_dc:
                    print(f'[direct] 失败，回退 swarm: {_e_dc}')

                # B2: fast 单 Agent（失败自动回退 strict）
                if _should_fast(agent_mode, content, enabled_tool_ids):
                    try:
                        from .. import fast_agent as _fa
                        _fr = await _fa.run_fast(
                            user_id, conversation_id, _ai_content,
                            allowed_tool_ids=enabled_tool_ids,
                            max_steps=(max_steps if (max_steps and max_steps > 0) else 8),
                        )
                        _freply = (_fr.get("content") or "").strip()
                        if _freply:
                            with db_cursor(commit=True) as _cur_f:
                                _cur_f.execute(
                                    "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)",
                                    (conversation_id, _freply, sender_agent_id or 'sases_assistant_2', msg_type, _att_str))
                                _cur_f.execute(
                                    "UPDATE conversations SET updated_at=? WHERE id=?",
                                    (datetime.now().isoformat(), conversation_id))
                            print("[fast] ok steps=" + str(_fr.get("steps")))
                            return {
                                'conversation_id': conversation_id,
                                'user_message': content,
                                'assistant_reply': _freply,
                                'agent_id': agent_id,
                                'sender_agent_id': sender_agent_id,
                                'mode': mode,
                                'fast_mode': True,
                                'steps': _fr.get("steps"),
                            }
                        print("[fast] 空结果，回退 strict")
                    except Exception as _e_f:
                        print("[fast] 失败，回退 strict: " + str(_e_f))

                # 调度员提议执行（对话模式）
                _skip_propose = False
                for _kw in ('harness', 'module_id', 'file_patch', 'web_fetch', 'git_ops', 'HARNESS:', 'run_python', 'file_read', 'grep_code', 'dir_tree'):
                    if _kw in content:
                        _skip_propose = True
                        break

                if sender_agent_id and not content.startswith('#') and not _skip_propose:
                    try:
                        from .. import supervisor_service
                        _ctx2 = supervisor_service.build_context(user_id, conversation_id, content, mode='execute', supervisor_id=sender_agent_id or agent_id)
                        _p2 = '你是 SASES 调度员。用户可能在对话中提出想让系统做的事。\n\n上下文：' + _ctx2 + '\n\n用户消息：' + content[:300] + '\n\n如果用户消息是明确的执行请求（要改代码/加功能/跑任务），输出 JSON：{"propose": true, "goal": "具体任务描述"}\n否则输出：{"propose": false}\n只输出 JSON，不要其他文字。'
                        import openai as _oai2
                        from ... import config as _cfg2
                        _c2 = _oai2.OpenAI(api_key=_cfg2.DEEPSEEK_API_KEY, base_url=_cfg2.DEEPSEEK_BASE_URL, timeout=15)
                        _r2 = _c2.chat.completions.create(model=_cfg2.MODEL_NAME, messages=[{'role': 'user', 'content': _p2}], temperature=0.2, max_tokens=150)
                        _raw2 = (_r2.choices[0].message.content or '').strip()
                        _i2 = _raw2.find('{')
                        _j2 = _raw2.rfind('}')
                        if _i2 >= 0 and _j2 > _i2:
                            import json as _j2mod
                            _dec = _j2mod.loads(_raw2[_i2:_j2+1])
                            if _dec.get('propose') and _dec.get('goal'):
                                _rid = supervisor_service.create_proposed_run(user_id, conversation_id, sender_agent_id, _dec['goal'], task_type=_classify_task_type(_dec['goal']))
                                print('[supervisor] 提议执行 run_id=' + str(_rid) + ' goal=' + _dec['goal'][:50])
                                with db_cursor(commit=True) as _c3:
                                    _c3.execute(
                                        "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)",
                                        (conversation_id, '【提议执行】' + _dec['goal'][:80], sender_agent_id, msg_type, _att_str)
                                    )
                                return {
                                    'conversation_id': conversation_id,
                                    'user_message': content,
                                    'assistant_reply': '【提议执行】' + _dec['goal'][:80],
                                    'agent_id': agent_id,
                                    'sender_agent_id': sender_agent_id,
                                    'mode': mode,
                                    'proposed_run_id': _rid
                                }
                    except Exception as _e2:
                        print('[supervisor] 提议检查失败: ' + str(_e2))

                # 调度者回执（v0.18.0 带上下文）
                if sender_agent_id:
                    try:
                        _receipt = "收到，我来处理。"
                        try:
                            from .. import supervisor_service
                            _ctx = supervisor_service.build_context(user_id, conversation_id, content, mode='execute', supervisor_id=sender_agent_id or agent_id)
                            _prompt = '你是调度助手。基于以下上下文，用一句话（不超过30字）回应用户，像真人说话，不要复述用户原话。上下文：' + _ctx + ' 用户新消息：' + content[:200] + ' 只输出这一句话。'
                            import openai as _oai
                            from ... import config as _cfg
                            _client = _oai.OpenAI(api_key=_cfg.DEEPSEEK_API_KEY, base_url=_cfg.DEEPSEEK_BASE_URL, timeout=15)
                            _resp = _client.chat.completions.create(model=_cfg.MODEL_NAME, messages=[{'role': 'user', 'content': _prompt}], temperature=0.7, max_tokens=80)
                            _ai_receipt = (_resp.choices[0].message.content or '').strip().strip('"').strip()
                            _too_similar = False
                            if _ai_receipt and content:
                                _c_norm = content.strip()[:50]
                                if _c_norm and _c_norm in _ai_receipt:
                                    _too_similar = True
                            if _ai_receipt and len(_ai_receipt) <= 60 and not _too_similar:
                                _receipt = _ai_receipt
                        except Exception as _ce:
                            print(f"[supervisor] 回执生成失败，用默认: {_ce}")
                        with db_cursor(commit=True) as _cur:
                            _cur.execute(
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)",
                                (conversation_id, _receipt, sender_agent_id, msg_type, _att_str)
                            )
                            _cur.execute(
                                "UPDATE conversations SET updated_at=? WHERE id=?",
                                (datetime.now().isoformat(), conversation_id)
                            )
                    except Exception as _e:
                        print(f"[supervisor] 回执失败: {_e}")

                # FIX_RUN_ID_v2: plan_task 前补建 run
                if not locals().get('_supervisor_run_id'):
                    try:
                        from ..supervisor import runs as _runs_v2
                        from ..supervisor_service import classify_task_type as _ctt_v2  # 若无则走下面兜底
                    except Exception:
                        _runs_v2 = None
                        _ctt_v2 = None
                    if _runs_v2:
                        try:
                            _tt_v2 = _ctt_v2(content) if _ctt_v2 else 'swarm'
                            _mr_v2 = max_steps if max_steps else None
                            _sup_v2 = sender_agent_id or agent_id or ""
                            _supervisor_run_id = _runs_v2.create_run(
                                user_id, conversation_id, _sup_v2, content,
                                task_type=_tt_v2, max_rounds=_mr_v2
                            )
                            print("[FIX_RUN_ID_v2] 主流程补建 run_id=" + str(_supervisor_run_id) + " conv=" + str(conversation_id))
                        except Exception as _e_v2:
                            print("[FIX_RUN_ID_v2] 补建失败: " + str(_e_v2))
                            _supervisor_run_id = None

                plan_result = await swarm_service.plan_task(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_input=content,
                    require_confirmation=require_confirmation,
                    supervisor_id=sender_agent_id,
                    supervisor_run_id=locals().get('_supervisor_run_id'),
                    enabled_api_ids=enabled_api_ids,
                    enabled_tool_ids=enabled_tool_ids,
                    enabled_skill_ids=enabled_skill_ids,
                )
                print(f"[MSG_DEBUG] plan_result={plan_result}")

                if plan_result is None:
                    reply = "任务拆解失败（格式错误），请重试或换一种说法。"
                    return {
                        "conversation_id": conversation_id,
                        "user_message": content,
                        "assistant_reply": reply,
                        "agent_id": agent_id,
                    }
                status = plan_result.get("status", "")
                if status == "draft":
                    reply = "已生成任务草稿，请在下方编辑后确认执行。"
                elif status == "planned":
                    reply = "已启动执行，请稍候…"
                elif status == "no_plan":
                    reply = "没有识别出可执行的命令。如果这不是任务，请点下方按钮。"
                elif status == "no_agent":
                    reply = "未找到可用智能体，请先在模型管理中创建。"
                else:
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
                    "assistant_reply": reply,
                    "agent_id": agent_id,
                    "sender_agent_id": sender_agent_id,
                    "mode": mode,
                    "swarm": True,
                    "swarm_status": status,
                    "task_id": plan_result.get("task_id"),
                    "steps": plan_result.get("steps", [])
                }
        except Exception as e:
            import traceback
            print(f"[MSG_DEBUG] 分流异常: {e}")
            traceback.print_exc()

    # ========== 蜂群模式：执行者汇报 [STEP_DONE] ==========
    if content.startswith("[STEP_DONE]:") and sender_agent_id:
        try:
            step_payload = json.loads(content[len("[STEP_DONE]:"):])
        except json.JSONDecodeError:
            return {"status": "error", "message": "步骤汇报格式错误"}

        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'assistant', ?, ?, ?, ?)",
                (conversation_id, content, sender_agent_id, msg_type, _att_str)
            )
            cur.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (datetime.now().isoformat(), conversation_id)
            )

        from .. import swarm_service
        swarm_result = await swarm_service.handle_step_done(conversation_id, step_payload, sender_agent_id)

        return {
            "status": "step_received",
            "conversation_id": conversation_id,
            "sender_agent_id": sender_agent_id,
            "swarm": swarm_result
        }

    # ========== 自由模式下执行指令 ==========
    if mode == "free" and content.startswith("执行："):
        command = content.replace("执行：", "", 1).strip()
        if not command:
            return {
                "conversation_id": conversation_id,
                "user_message": content,
                "assistant_reply": "请提供要执行的命令",
                "agent_id": agent_id,
                "sender_agent_id": sender_agent_id,
                "mode": mode
            }
        try:
            work_result = await work_service.execute_work_command(
                user_id=user_id,
                conversation_id=conversation_id,
                command=command,
                sender_agent_id=sender_agent_id
            )
            return {
                "conversation_id": conversation_id,
                "user_message": content,
                "assistant_reply": work_result["output"],
                "agent_id": agent_id,
                "sender_agent_id": sender_agent_id,
                "mode": mode,
                "work_result": work_result
            }
        except Exception as e:
            return {
                "conversation_id": conversation_id,
                "user_message": content,
                "assistant_reply": f"指令执行失败：{str(e)}",
                "agent_id": agent_id,
                "sender_agent_id": sender_agent_id,
                "mode": mode
            }

    # ========== 蜂群模式在单聊中不支持 ==========
    if mode == "swarm":
        return {
            "conversation_id": conversation_id,
            "user_message": content,
            "assistant_reply": "蜂群模式仅在群聊中可用，请切换到群聊或使用其他模式。",
            "agent_id": agent_id,
            "sender_agent_id": sender_agent_id,
            "mode": mode
        }

    # ========== 普通模式或自由模式下的普通消息 ==========
    if not conversation_id:
        title = "新会话"
        if agent_id:
            with db_cursor() as cur:
                cur.execute("SELECT name FROM model_configs WHERE id=?", (agent_id,))
                row = cur.fetchone()
                if row:
                    title = row["name"]
        conversation_id = create_conversation(user_id, agent_id, title)

    with db_cursor(commit=True) as cur:
        if sender_agent_id:
            cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id, msg_type, attachments) VALUES (?, 'user', ?, ?, ?, ?)",
                        (conversation_id, content, sender_agent_id, msg_type, _att_str))
        else:
            cur.execute("INSERT INTO messages (conversation_id, sender, content, msg_type, attachments) VALUES (?, 'user', ?, ?, ?)",
                        (conversation_id, content, msg_type, _att_str))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))

    if agent_id:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM model_configs WHERE id=? AND user_id=?", (agent_id, user_id))
            model_row = cur.fetchone()
        if not model_row:
            # 【新增】SASES 助手作为留言板，不报错
            _is_sases_assist = str(agent_id or '').startswith('sases_assistant')
            if _is_sases_assist:
                assistant_reply = "📢 留言已收到，系统管理员上线后会处理你的反馈。"
            else:
                assistant_reply = "错误：找不到绑定的智能体模型"
        else:
            model_config = dict(model_row)
            # 项目库检索（v0.17.0）— 仅 SASES 助手
            _is_sases_chat = True  # inject
            _is_import_local = (            '导入知识库' in content or '加入知识库' in content or '存到知识库' in content or '存到项目库' in content or '导入项目库' in content or '加到知识库' in content)
            enriched_query = content
            if _is_sases_chat and not _is_import_local:
                try:
                    from .. import project_service
                    chunks = project_service.retrieve_project_chunks(content, top_k=3, threshold=0.35, user_id=user_id)
                    print(f"[chunks_DEBUG] user_id={user_id} count={len(chunks)}")
                    if chunks:
                        _top = chunks[0].get("score", 0)
                        if _top > 0.55:
                            project_text = project_service.format_chunks_for_prompt(chunks)
                            enriched_query = (project_text + "\n\n" + content) if project_text else content
                            print(f"[message] 项目库高分命中 {_top:.3f}(含 task_context)")
                        else:
                            _ctx_lo = project_service.format_chunks_for_prompt(chunks)
                            enriched_query = (_ctx_lo + "\n\n" + content) if _ctx_lo else content
                            print(f"[message] 项目库低分兜底 {_top:.3f}")
                    else:
                        enriched_query = content
                        print(f"[message] 项目库无匹配，仅注入历史")
                except Exception as e:
                    print(f"[message] 项目库检索失败: {e}")
            else:
                try:
                    enriched_query = content
                    print(f"[message] 非 SASES 助手，仅注入历史")
                except Exception as e:
                    print(f"[message] 上下文注入失败: {e}")
            try:
                assistant_reply = await call_model_with_config(model_config, enriched_query)
            except Exception as e:
                assistant_reply = f"模型调用失败：{str(e)}"
    else:
        assistant_reply = "请先在“我的→模型管理”中配置模型，或从智能体页面发起对话"

    from .reply import insert_message as _insert_reply
    _insert_reply(conversation_id, assistant_reply, msg_type=msg_type, attachments=_att_str)

    try:
        from ...api_routes.ws_routes import broadcast_to_user as _bc_user
        await _bc_user(user_id, {'type': 'new_message', 'conversation_id': conversation_id, 'sender': 'assistant', 'preview': (assistant_reply or '')[:80]})
    except Exception as _e_bc:
        print('[ws] broadcast failed: ' + str(_e_bc))

    return {
        "conversation_id": conversation_id,
        "user_message": content,
        "assistant_reply": assistant_reply,
        "agent_id": agent_id,
        "sender_agent_id": sender_agent_id,
        "mode": mode
    }