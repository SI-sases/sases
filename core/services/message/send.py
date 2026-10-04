import base64
import json
import httpx
from datetime import datetime
from typing import Optional
from ...db import db_cursor


def _sases_fallback_cid():
    try:
        with db_cursor() as _sases_cur:
            _sases_cur.execute("SELECT conversation_id FROM messages WHERE sender='user' ORDER BY id DESC LIMIT 1")
            _sases_row = _sases_cur.fetchone()
            if _sases_row:
                try:
                    _sases_val = _sases_row['conversation_id']
                except Exception:
                    _sases_val = _sases_row[0]
                if _sases_val:
                    print('[supervisor] auto_run fallback conversation_id=' + str(_sases_val))
                    return _sases_val
    except Exception:
        pass
    return 0

from .constants import REQUIRE_TASK_CONFIRMATION, COMMAND_PREFIX_MAP, DRAFT_PREFIXES
from .conversations import create_conversation, get_messages, mark_conversation_read
from .model_call import call_model_with_config
from .attachments import _enrich_attachment

def _classify_task_type(goal):
    _g = str(goal or '')
    if any(k in _g for k in ('探测', '列出', '统计', '看', '读')):
        return 'simple_probe'
    if any(k in _g for k in ('重构', '重写', '打通')):
        return 'refactor'
    if any(k in _g for k in ('加', '实现', '新增', '创建', '参考')):
        return 'feature_dev'
    if any(k in _g for k in ('改', '修')):
        return 'code_edit'
    return 'unknown'


async def send_message(
    user_id: int,
    conversation_id: int,
    agent_id: str,
    content: str,
    sender_agent_id: str = None,
    mode: str = "normal"
):
    print(f"[MSG_DEBUG] content={content!r} | mode={mode!r} | agent_id={agent_id!r}")


    # #5 清锁（最先拦截，绕过所有锁检查）
    if isinstance(content, str) and content.strip().startswith('#5'):
        try:
            from .. import swarm_service as _sw5
            _cl = _sw5.clear_conversation_lock(conversation_id)
            _msg = '已清除会话锁' if _cl else '无活跃锁'
        except Exception as _e5:
            _msg = '清锁失败: ' + str(_e5)
        if conversation_id:
            try:
                with db_cursor(commit=True) as _c5:
                    _c5.execute(
                        "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                        (conversation_id, _msg, sender_agent_id or agent_id)
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
            _c.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'user', ?, ?)", (conversation_id, content, sender_agent_id))
            _c.execute('UPDATE conversations SET updated_at=? WHERE id=?', (datetime.now().isoformat(), conversation_id))
        # 关键改动：把附件内容附加进来，不再 return，继续走正常问答
        try:
            content = _enrich_attachment(content)
        except Exception as _e:
            print('[message] enrich 失败: ' + str(_e))



    # ========== 检测草稿前缀 ==========
    require_confirmation = REQUIRE_TASK_CONFIRMATION
    # 检测 #1~#4 编号前缀
    _numbered_prefix_matched = False
    _force_swarm = False
    for _p, _m in COMMAND_PREFIX_MAP.items():
        if content.startswith(_p):
            _numbered_prefix_matched = True
            content = content[len(_p):].lstrip()
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
                    _run_id = supervisor_service.create_run(user_id, _cid_auto, sender_agent_id or agent_id, content, task_type=_classify_task_type(content))
                    print("[supervisor] 已创建 run_id=" + str(_run_id) + " goal=" + content[:50])
                    _force_swarm = True
                    _supervisor_run_id = _run_id
                    from .. import swarm_service
                    try:
                        await swarm_service.plan_task(
                            user_id=user_id,
                            conversation_id=_cid_auto,
                            user_input=content,
                            supervisor_id=sender_agent_id or agent_id,
                            supervisor_run_id=_run_id,
                        )
                        print("[supervisor] auto_run 已派单 run_id=" + str(_run_id))
                    except Exception as _ae:
                        print("[supervisor] auto_run 派单失败: " + str(_ae))
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
                content.startswith('*1:') or content.startswith('*1：')
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
                        from .. import context_service
                        _ans_prompt = context_service.build_enriched_prompt(user_id, conversation_id, content, _ctx)
                        if agent_id:
                            with db_cursor() as _cur:
                                _cur.execute('SELECT * FROM model_configs WHERE id=? AND user_id=?', (agent_id, user_id))
                                _mr = _cur.fetchone()
                            if _mr:
                                _mr = dict(_mr)
                                with db_cursor(commit=True) as _cur:
                                    _cur.execute('INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)', (conversation_id, 'user', content))
                                try:
                                    _reply = await call_model_with_config(_mr, _ans_prompt)
                                except Exception as _e:
                                    _reply = '模型调用失败: ' + str(_e)
                                with db_cursor(commit=True) as _cur:
                                    _cur.execute('INSERT INTO messages (conversation_id, sender, content) VALUES (?, ?, ?)', (conversation_id, 'assistant', _reply))
                                    _cur.execute('UPDATE conversations SET updated_at=? WHERE id=?', (datetime.now().isoformat(), conversation_id))
                                print('[message] 项目库快速回答命中，相似度 ' + str(round(_chunks[0].get('score', 0), 3)))
                                return {'conversation_id': conversation_id, 'user_message': content, 'assistant_reply': _reply, 'agent_id': agent_id, 'sender_agent_id': sender_agent_id, 'mode': mode, 'project_kb_hit': True}
                except Exception as _e:
                    print('[message] 项目库快速回答失败: ' + str(_e))

            if _force_swarm:
                is_task = True
            else:
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
                                    _cwi.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)", (conversation_id, _img_reply, sender_agent_id or agent_id))
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
            if True:  # v0.18: 所有用户都能 *1 投喂个人知识库
                for _up in ('*1：', '*1:'):
                    if content.startswith(_up):
                        _uni_body = content[len(_up):].strip()
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
            if not _uni_text and isinstance(content, str) and content.startswith(('*1:', '*1：')):
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
                            _cin_img.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)", (conversation_id, _img_rep, sender_agent_id))
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
                        _cin_uni.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)", (conversation_id, _urep, sender_agent_id))
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
                        _cin.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)", (conversation_id, _irep_inline, sender_agent_id))
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
                        _cwi.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)", (conversation_id, _irep, sender_agent_id))
                        _cwi.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))
                    return {'conversation_id': conversation_id, 'user_message': content, 'assistant_reply': _irep, 'agent_id': agent_id, 'sender_agent_id': sender_agent_id, 'mode': mode, 'import_mode': True}
                except Exception as _ei:
                    print('[supervisor] 导入失败: ' + str(_ei))


            # 对话模式（v0.18.0）：非任务、非技术指令、非问候，直接回答
            pass
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
                    pass

                    pass

                    if _chat_reply:
                        with db_cursor(commit=True) as _ccur:
                            _ccur.execute(
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                                (conversation_id, _chat_reply, sender_agent_id)
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
                if not conversation_id:
                    title = "蜂群任务"
                    if agent_id:
                        with db_cursor() as cur:
                            cur.execute("SELECT name FROM model_configs WHERE id=?", (agent_id,))
                            row = cur.fetchone()
                            if row:
                                title = row["name"]
                    conversation_id = create_conversation(user_id, agent_id, title)

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
                                        "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                                        (conversation_id, '【提议执行】' + _dec['goal'][:80], sender_agent_id)
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


                # (旧对话模式已删)
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
                                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                                (conversation_id, _receipt, sender_agent_id)
                            )
                            _cur.execute(
                                "UPDATE conversations SET updated_at=? WHERE id=?",
                                (datetime.now().isoformat(), conversation_id)
                            )
                    except Exception as _e:
                        print(f"[supervisor] 回执失败: {_e}")

                plan_result = await swarm_service.plan_task(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    user_input=content,
                    require_confirmation=require_confirmation,
                    supervisor_id=sender_agent_id,
                    supervisor_run_id=locals().get('_supervisor_run_id')
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
                "INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'assistant', ?, ?)",
                (conversation_id, content, sender_agent_id)
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
            cur.execute("INSERT INTO messages (conversation_id, sender, content, sender_agent_id) VALUES (?, 'user', ?, ?)",
                        (conversation_id, content, sender_agent_id))
        else:
            cur.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                        (conversation_id, content))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))

    if agent_id:
        with db_cursor() as cur:
            cur.execute("SELECT * FROM model_configs WHERE id=? AND user_id=?", (agent_id, user_id))
            model_row = cur.fetchone()
        if not model_row:
            assistant_reply = "错误：找不到绑定的智能体模型"
        else:
            model_config = dict(model_row)
            # 项目库检索（v0.17.0）— 仅 SASES 助手
            _is_sases_chat = 'sases' in (model_config.get('name') or '').lower()
            _is_import_local = (            '导入知识库' in content or '加入知识库' in content or '存到知识库' in content or '存到项目库' in content or '导入项目库' in content or '加到知识库' in content)
            enriched_query = content
            if _is_sases_chat and not _is_import_local:
                try:
                    from .. import project_service
                    chunks = project_service.retrieve_project_chunks(content, top_k=3, threshold=0.35, user_id=user_id)
                    if chunks:
                        _top = chunks[0].get("score", 0)
                        if _top > 0.55:
                            project_text = project_service.format_chunks_for_prompt(chunks)
                            enriched_query = project_text + "\n\n【用户问题】\n" + content
                            print(f"[message] 项目库高分命中 {_top:.3f}")
                        else:
                            from .. import context_service
                            _ctx_lo = project_service.format_chunks_for_prompt(chunks)
                            enriched_query = context_service.build_enriched_prompt(user_id, conversation_id, content, _ctx_lo)
                            print(f"[message] 项目库低分兜底 {_top:.3f}")
                    else:
                        from .. import context_service
                        enriched_query = context_service.build_enriched_prompt(user_id, conversation_id, content, "")
                        print(f"[message] 项目库无匹配，仅注入历史")
                except Exception as e:
                    print(f"[message] 项目库检索失败: {e}")
            else:
                try:
                    from .. import context_service
                    enriched_query = context_service.build_enriched_prompt(user_id, conversation_id, content, "")
                    print(f"[message] 非 SASES 助手，仅注入历史")
                except Exception as e:
                    print(f"[message] 上下文注入失败: {e}")
            try:
                assistant_reply = await call_model_with_config(model_config, enriched_query)
            except Exception as e:
                assistant_reply = f"模型调用失败：{str(e)}"
    else:
        assistant_reply = "请先在“我的→模型管理”中配置模型，或从智能体页面发起对话"

    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'assistant', ?)",
                    (conversation_id, assistant_reply))
        cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (datetime.now().isoformat(), conversation_id))

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

