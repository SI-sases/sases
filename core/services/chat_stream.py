# core/services/chat_stream.py
# -*- coding: utf-8 -*-
"""UX-2: 聊天类消息的流式回答。"""
import asyncio
import threading

from ..db import db_cursor


async def stream_chat(user_id: int, conversation_id: int, content: str, quote_content=None, max_tokens: int = 1200):
    from .unified_context import build_context
    from .swarm.llm_parser import client, MODEL

    _CHAT_SYSTEM = ("你是 SASES 的对话助手。用简洁中文直接回答用户；"
                    "不要输出【分析】【步骤】、JSON、计划或工具调用；"
                    "如果用户要执行任务，简短说明并让对方直接说需求。")

    try:
        ctx, _ = build_context(user_id, conversation_id, content, mode="chat")
    except Exception:
        ctx = content
    if quote_content:
        ctx = "【引用消息】\n" + str(quote_content)[:1000] + "\n\n【用户消息】\n" + ctx

    messages = [
        {"role": "system", "content": _CHAT_SYSTEM},
        {"role": "user", "content": ctx},
    ]
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()

    def worker():
        try:
            stream = client.chat.completions.create(
                model=MODEL, messages=messages, temperature=0.6,
                max_tokens=max_tokens, stream=True,
            )
            for ch in stream:
                try:
                    delta = ch.choices[0].delta.content
                except Exception:
                    delta = None
                if delta:
                    asyncio.run_coroutine_threadsafe(q.put(("t", delta)), loop).result()
            asyncio.run_coroutine_threadsafe(q.put(("end", None)), loop).result()
        except Exception as e:
            asyncio.run_coroutine_threadsafe(q.put(("err", str(e))), loop).result()

    threading.Thread(target=worker, daemon=True).start()

    full = []
    while True:
        kind, val = await q.get()
        if kind == "t":
            full.append(val)
            yield {"type": "token", "text": val}
        elif kind == "err":
            yield {"type": "error", "error": val}
            return
        else:
            break

    text = "".join(full).strip()
    if not text:
        yield {"type": "error", "error": "模型没有返回内容"}
        return

    try:
        import datetime
        now = datetime.datetime.now().isoformat()
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'user', ?)",
                (conversation_id, content))
            cur.execute(
                "INSERT INTO messages (conversation_id, sender, content) VALUES (?, 'assistant', ?)",
                (conversation_id, text))
            mid = cur.lastrowid
            cur.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
    except Exception as e:
        print("[stream] 保存消息失败: " + str(e))
        mid = None

    yield {"type": "final", "conversation_id": conversation_id, "message_id": mid,
           "assistant_reply": text}
