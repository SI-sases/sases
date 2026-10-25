# -*- coding: utf-8 -*-
import time
from core.services import memory_service

USER_ID = 5  # 666666 的 user_id，如不确定先查数据库

print("=" * 60)
print("测试 1：写入记忆")
print("=" * 60)
mid = memory_service.remember(
    user_id=USER_ID,
    memory_type="task_result",
    content="用户查询了 core 目录下的文件列表",
    task_id="t_test_001",
    importance=0.5,
    tags="file_query,core"
)
print(f"写入 memory_id = {mid}")

print()
print("=" * 60)
print("测试 2：hash 去重（相同内容）")
print("=" * 60)
mid2 = memory_service.remember(
    user_id=USER_ID,
    memory_type="task_result",
    content="用户查询了 core 目录下的文件列表",
    task_id="t_test_002",
    importance=0.5
)
print(f"第二次写入 memory_id = {mid2}  {'✅ 去重成功' if mid2 == mid else '❌ 未去重'}")

print()
print("=" * 60)
print("测试 3：语义去重（相似内容）")
print("=" * 60)
time.sleep(0.5)
mid3 = memory_service.remember(
    user_id=USER_ID,
    memory_type="task_result",
    content="用户查看了 core 目录的文件列表",
    task_id="t_test_003",
    importance=0.5
)
print(f"相似内容写入 memory_id = {mid3}  {'✅ 语义去重成功' if mid3 == mid else '⚠️ 视为新记忆'}")

print()
print("=" * 60)
print("测试 4：语义检索")
print("=" * 60)
results = memory_service.recall(
    user_id=USER_ID,
    query="目录文件",
    top_k=5
)
print(f"检索到 {len(results)} 条：")
for r in results:
    print(f"  [sim={r.get('_similarity', '?')}] {r['content'][:60]}")
