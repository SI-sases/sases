# -*- coding: utf-8 -*-
import asyncio
import sys
sys.path.insert(0, ".")

from core.services import intent_service

async def main():
    tests = ["你好", "今天天气怎么样", "列出当前目录", "帮我看看D盘有什么"]
    for t in tests:
        result = await intent_service.is_task_intent(t)
        print(f"{t!r:25} -> is_task = {result}")

asyncio.run(main())
