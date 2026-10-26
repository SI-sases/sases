# -*- coding: utf-8 -*-
import numpy as np
from core.services import memory_service
from core.db import db_cursor

USER_ID = 5

# 1. 查看已存储的 embedding
print("=" * 60)
print("已存储的记忆（含 embedding 状态）")
print("=" * 60)
with db_cursor() as cur:
    cur.execute(
        "SELECT id, content, length(embedding) as emb_len FROM safety_memory WHERE user_id=? ORDER BY id DESC LIMIT 5",
        (USER_ID,)
    )
    for r in cur.fetchall():
        print(f"#{r['id']} | emb_len={r['emb_len']} | {r['content'][:50]}")

# 2. 直接计算两句话的相似度
print()
print("=" * 60)
print("直接计算相似度")
print("=" * 60)
from core.services.local_embedding import LocalEmbedding
emb = LocalEmbedding()

def to_vec(x):
    v = np.asarray(x, dtype=np.float32)
    return v.flatten()

pairs = [
    ("用户查询了 core 目录下的文件列表", "用户查看了 core 目录的文件列表"),
    ("用户查询了 core 目录下的文件列表", "目录文件"),
    ("用户查询了 core 目录下的文件列表", "用户询问了当前登录的用户名"),
    ("目录文件", "列出目录"),
    ("目录文件", "当前登录用户"),
]

for a, b in pairs:
    ea = to_vec(emb.get_embedding(a))
    eb = to_vec(emb.get_embedding(b))
    sim = float(np.dot(ea, eb) / (np.linalg.norm(ea) * np.linalg.norm(eb)))
    print(f"{sim:.4f} | {a[:20]} <-> {b[:20]}")
