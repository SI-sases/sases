# core/services/chat_stream.py
# -*- coding: utf-8 -*-
"""UX-2: 聊天类消息的流式回答。"""
import asyncio
import threading

from ..db import db_cursor


async def stream_chat(user_id: int, conversation_id: int, content: str, quote_content=None, max_tokens: int = 1200):
    from .agent_memory import backfill as _am_backfill, history as _am_history
    from .agent_compact import maybe_compact as _maybe_compact
    from .swarm.prompts import BASE_SYSTEM
    from .swarm.llm_parser import client, MODEL

    try:
        await _maybe_compact(conversation_id, user_id)
    except Exception as e:
        print("[stream] compact 跳过: " + str(e))
    try:
        _am_backfill(conversation_id)
        hist = _am_history(conversation_id)
    except Exception:
        hist = []

    messages = [{
        "role": "system",
        "content": BASE_SYSTEM + "\n【角色：聊天】简洁中文直接回答；不要输出计划、JSON 或工具调用。",
    }] + hist
    if quote_content:
        messages.append({"role": "user", "content": "【引用消息】\n" + str(quote_content)[:1000]})
    messages.append({"role": "user", "content": content})
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
        try:
            from . import agent_memory as _am_s
            _am_s.append(conversation_id, "user", content)
            _am_s.append(conversation_id, "assistant", text)
        except Exception as _e_am:
            print("[agent_memory] stream 双写失败: " + str(_e_am))
    except Exception as e:
        print("[stream] 保存消息失败: " + str(e))
        mid = None

    yield {"type": "final", "conversation_id": conversation_id, "message_id": mid,
           "assistant_reply": text}
