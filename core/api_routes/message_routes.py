# core/api_routes/message_routes.py
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import message_service

router = APIRouter(prefix="/messages", tags=["messages"])
security = HTTPBearer()

_WRITE_ACTIONS = ("改", "修改", "修复", "创建", "新建", "写入", "删除", "移除",
                  "重命名", "移动", "复制", "替换", "重构", "实现", "添加",
                  "加一个", "部署", "安装", "更新", "保存", "生成", "导出", "导入")
_READ_ACTIONS = ("读取", "查看", "看一下", "看下", "看看", "读一下", "读读",
                 "查一下", "查查", "查找", "搜索", "统计",
                 "汇总", "分析", "检查", "测试", "运行", "执行")
_OBJECT_WORDS = ("文件", "目录", "路径", "代码", "脚本", "页面", "样式", "配置",
                 "接口", "函数", "模块", "bug", "报错", "html", "js", "py", "css", "json", "md")


def _is_smalltalk(text):
    s = str(text or "").strip().lower()
    if not s:
        return True
    if len(s) > 60:
        return False
    exact = ("你好", "您好", "hi", "hello", "在吗", "在不在", "谢谢", "多谢",
             "好的", "好", "收到", "嗯", "哈哈", "再见", "拜拜", "晚安", "早安",
             "你是谁", "你能做什么", "介绍一下你自己")
    if s in exact:
        return True
    return any(s.startswith(x) for x in ("你好", "您好", "谢谢", "再见", "晚安")) and len(s) <= 20


def _looks_like_task(text):
    s = str(text or "").strip()
    if not s:
        return False
    if any(v in s for v in _WRITE_ACTIONS):
        return True
    # 提到具体文件/代码时，即使是“是什么/在哪”也交给执行链路读文件
    if re.search(r"[A-Za-z0-9_./\\-]+\.(py|js|mjs|md|json|html|css|yml|yaml|txt)\b", s, re.I):
        return True
    if any(v in s for v in _READ_ACTIONS):
        return len(s) >= 12 or any(o in s.lower() for o in _OBJECT_WORDS)
    return False



class SendMessageRequest(BaseModel):
    enabled_api_ids: list = None
    enabled_tool_ids: list = None
    enabled_skill_ids: list = None
    agent_mode: Optional[str] = None
    quote_content: Optional[str] = None
    msg_type: Optional[str] = "standard"
    attachments: Optional[list] = None
    conversation_id: Optional[int] = None
    agent_id: Optional[str] = None
    content: str
    sender_agent_id: Optional[str] = None
    mode: Optional[str] = "normal"  # normal / free / swarm
    max_steps: Optional[int] = None  # -1=不限，None=默认8


class ConversationCreateRequest(BaseModel):
    agent_id: Optional[str] = None
    title: Optional[str] = "新会话"


class StreamMessageRequest(BaseModel):
    conversation_id: int
    content: str
    sender_agent_id: Optional[str] = None
    msg_type: Optional[str] = "standard"
    attachments: Optional[list] = None
    quote_content: Optional[str] = None
    enabled_skill_ids: Optional[list] = None


class PinRequest(BaseModel):
    pinned: bool


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/conversations")
async def list_conversations(user_id: int = Depends(get_current_user)):
    conversations = message_service.list_conversations(user_id)
    return {"conversations": conversations}


@router.post("/conversations")
async def create_conversation(body: ConversationCreateRequest, user_id: int = Depends(get_current_user)):
    conv_id = message_service.create_conversation(user_id, body.agent_id, body.title)
    return {"conversation_id": conv_id, "title": body.title, "agent_id": body.agent_id}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    after_id: Optional[int] = None,
    user_id: int = Depends(get_current_user)
):
    messages = message_service.get_messages(user_id, conversation_id, limit, offset, after_id)
    if messages is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"messages": messages}


def _sse(obj) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False, default=str) + "\n\n"


@router.post("/stream")
async def stream_message(body: StreamMessageRequest, user_id: int = Depends(get_current_user)):
    async def gen():
        try:
            from ..db import db_cursor
            with db_cursor() as cur:
                cur.execute("SELECT 1 FROM conversations WHERE id=? AND user_id=?",
                            (body.conversation_id, user_id))
                if not cur.fetchone():
                    yield _sse({"type": "error", "error": "会话不存在"})
                    return

            # 统一入口：只有显式执行/附件/非标准消息才进入 strict loop；
            # 其余文本仍走同一个 agent 的聊天流，不再用语义意图决定角色链。
            _text = (body.content or "").strip()
            _explicit_exec = _text.startswith(("执行：", "执行:"))
            if _explicit_exec:
                _text = _text.split("：", 1)[-1] if "：" in _text else _text.split(":", 1)[-1]
                _text = _text.strip()
            from ..db import db_cursor
            with db_cursor() as cur:
                cur.execute("SELECT agent_id FROM conversations WHERE id=? AND user_id=?",
                            (body.conversation_id, user_id))
                _conv = cur.fetchone()
            _agent_id = _conv["agent_id"] if _conv else body.sender_agent_id
            _strict = (_explicit_exec
                       or _looks_like_task(_text)
                       or not _is_smalltalk(_text)
                       or _text.startswith("#")
                       or (body.msg_type and body.msg_type != "standard"))
            if _strict:
                from ..services.message.send import send_message
                res = await send_message(
                    user_id=user_id, conversation_id=body.conversation_id,
                    agent_id=_agent_id,
                    content=_text, sender_agent_id=body.sender_agent_id,
                    quote_content=body.quote_content,
                    enabled_skill_ids=body.enabled_skill_ids,
                    max_steps=12, agent_mode="strict")
                yield _sse({"type": "final", "data": res})
                return

            from ..services.chat_stream import stream_chat
            async for ev in stream_chat(user_id, body.conversation_id, body.content, body.quote_content,
                                        skill_ids=body.enabled_skill_ids):
                yield _sse(ev)
        except Exception as e:
            yield _sse({"type": "error", "error": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/send")
async def send_message(body: SendMessageRequest, user_id: int = Depends(get_current_user)):
    result = await message_service.send_message(
        user_id=user_id,
        conversation_id=body.conversation_id,
        agent_id=body.agent_id,
        content=body.content,
        sender_agent_id=body.sender_agent_id,
        mode=body.mode,
        enabled_api_ids=body.enabled_api_ids,
        enabled_tool_ids=body.enabled_tool_ids,
        enabled_skill_ids=body.enabled_skill_ids,
        agent_mode=body.agent_mode,
        quote_content=body.quote_content,
        max_steps=body.max_steps,
        msg_type=body.msg_type,
        attachments=body.attachments
    )
    try:
        from .ws_routes import broadcast_to_user
        await broadcast_to_user(user_id, {
            'type': 'new_message',
            'conversation_id': result.get('conversation_id'),
            'user_message': result.get('user_message'),
            'assistant_reply': result.get('assistant_reply'),
            'agent_id': result.get('agent_id'),
            'sender_agent_id': result.get('sender_agent_id'),
        })
    except Exception as _e:
        print('[ws] send push failed:', _e)

    # v0.38.0: 返回 write_hlc 供前端读己之写
    try:
        from ..db import db_cursor as _dbc
        _cid_hlc = result.get('conversation_id') if isinstance(result, dict) else None
        if _cid_hlc:
            with _dbc() as _cur_hlc:
                _cur_hlc.execute(
                    "SELECT hlc_ts FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 1",
                    (_cid_hlc,)
                )
                _row_hlc = _cur_hlc.fetchone()
                if _row_hlc and _row_hlc["hlc_ts"]:
                    result['write_hlc'] = _row_hlc["hlc_ts"]
    except Exception as _e_hlc:
        print('[hlc] write_hlc 附加失败:', _e_hlc)

    return result


@router.post("/{conversation_id}/read")
async def mark_read(conversation_id: int, user_id: int = Depends(get_current_user)):
    message_service.mark_conversation_read(user_id, conversation_id)
    return {"status": "read"}


@router.post("/{conversation_id}/pin")
async def toggle_pin(conversation_id: int, body: PinRequest, user_id: int = Depends(get_current_user)):
    message_service.toggle_pin_conversation(user_id, conversation_id, body.pinned)
    return {"status": "updated"}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: int, user_id: int = Depends(get_current_user)):
    message_service.delete_conversation(user_id, conversation_id)
    return {"status": "deleted"}


# ============ FIX_MENU_V2_DELETE: 单条消息删除 ============
@router.delete("/message/{message_id}")
async def delete_single_message(message_id: int, user: dict = Depends(get_current_user)):
    """删除单条消息（只能删自己会话里的）"""
    from ..db import db_cursor
    _uid = user.get("id") or user.get("user_id")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM messages WHERE id = ?", (message_id,))
        if not cur.fetchone():
            raise HTTPException(404, "消息不存在")
        cur.execute(
            "SELECT m.id FROM messages m "
            "JOIN conversations c ON m.conversation_id = c.id "
            "WHERE m.id = ? AND c.user_id = ?",
            (message_id, _uid),
        )
        if not cur.fetchone():
            raise HTTPException(403, "无权删除该消息")
        cur.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    return {"status": "deleted", "message_id": message_id}


# ============ FIX_EXECUTE_V2: 帮我执行 - 生成 #4 指令 ============
from pydantic import BaseModel as _BM_v2
from typing import List as _List_v2, Optional as _Opt_v2

class _SuggestExecReq(_BM_v2):
    messages: _Opt_v2[_List_v2[dict]] = None
    content: _Opt_v2[str] = None

@router.post("/messages/suggest-execute")
async def suggest_execute_route(body: _SuggestExecReq, user: dict = Depends(get_current_user)):
    """根据最近聊天上下文生成 #4 执行指令"""
    from ..config import MODEL
    from openai import OpenAI
    import os as _os_v2

    _msgs = body.messages or []
    if not _msgs and body.content:
        _msgs = [{"role": "user", "content": body.content}]

    if not _msgs:
        raise HTTPException(400, "缺少上下文")

    _ctx = ""
    for m in _msgs[-8:]:
        _who = "用户" if m.get("role") == "user" else "AI"
        _t = str(m.get("content", ""))[:1500]
        if _t:
            _ctx += _who + ": " + _t + "\n\n"

    _prompt = (
        "你是 SASES 的执行指令生成助手。用户刚在聊天中谈论了下面的内容，现在想让系统实际执行。\n\n"
        "【最近对话】\n" + _ctx + "\n"
        "【任务】\n"
        "请生成一条 #4 执行指令，让系统能理解并执行。严格按以下格式：\n"
        "#4: <一句话目标>。背景是 <必要背景（谁在哪个文件里改什么）>。"
        "要求：1. <具体步骤（点名文件+函数+动作）>。2. <验证方式（verify_syntax / grep / 跑测试）>。\n\n"
        "规则：\n"
        "- 必须有明确目标（不是\"优化逻辑\"这种模糊描述）\n"
        "- 必须点名文件路径或函数名\n"
        "- 必须包含验证步骤\n"
        "- 提炼整合上下文，不要照搬原话\n"
        "- 只输出 #4 指令本身，不要任何解释、不要 markdown 代码块、不要注释\n"
        "- 指令长度控制在 200-500 字\n"
    )

    try:
        _client = OpenAI(
            api_key=_os_v2.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=_os_v2.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        _resp = await asyncio.to_thread(
            _client.chat.completions.create,
            model=MODEL,
            messages=[{"role": "user", "content": _prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        _out = (_resp.choices[0].message.content or "").strip()
        # 清理可能的代码块包裹
        if _out.startswith("```"):
            _lines = _out.split("\n")
            _lines = _lines[1:]
            if _lines and _lines[-1].strip() == "```":
                _lines = _lines[:-1]
            _out = "\n".join(_lines).strip()
        # 保证以 #4: 开头
        if not _out.startswith("#4"):
            _out = "#4: " + _out
        print("[suggest-execute] 生成指令长度=" + str(len(_out)))
        return {"instruction": _out, "task": _out}
    except Exception as e:
        print("[suggest-execute] 生成失败: " + str(e))
        # 兜底：用原消息直接包成 #4
        _fallback = "#4: 请根据以下内容执行：" + (_msgs[-1].get("content", "")[:400] if _msgs else "")
        return {"instruction": _fallback, "task": _fallback}
