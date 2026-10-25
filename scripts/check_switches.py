import os

PATTERNS = ["ENABLE_GAME", "ENABLE_PATTERN_SYNC", "ENABLE_KB_SYNC", "ENABLE_CROSS_NODE_CREDIT"]
ROOTS = ["core", "static"]
EXTS = (".py", ".js")

hits = []
scanned = 0
for root_dir in ROOTS:
    if not os.path.exists(root_dir):
        print(f"[跳过] {root_dir} 不存在")
        continue
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith(EXTS):
                scanned += 1
                fp = os.path.join(dirpath, f)
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as fh:
                        for i, line in enumerate(fh, 1):
                            if any(p in line for p in PATTERNS):
                                hits.append(f"{fp}:{i}: {line.rstrip()}")
                except Exception as e:
                    print(f"[读取失败] {fp}: {e}")

print(f"扫描了 {scanned} 个文件")
if hits:
    print(f"\n找到 {len(hits)} 处：")
    for h in hits:
        print(h)
else:
    print("\n未找到任何 ENABLE_xxx 读取逻辑 —— 需要在 l1-server 分支注释掉相关路由和定时任务")
