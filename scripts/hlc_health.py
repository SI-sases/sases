# scripts/hlc_health.py
"""
HLC 地基健康度检查
输出到控制台 + docs/hlc_health/YYYYMMDD.md
"""
import os
import sys
import sqlite3

# v0.39.2: Windows GBK 控制台编码保护
import sys as _sys_h
import io as _io_h
if _sys_h.stdout.encoding and _sys_h.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    _sys_h.stdout = _io_h.TextIOWrapper(_sys_h.stdout.buffer, encoding='utf-8', errors='replace')
if _sys_h.stderr.encoding and _sys_h.stderr.encoding.lower() not in ('utf-8', 'utf8'):
    _sys_h.stderr = _io_h.TextIOWrapper(_sys_h.stderr.buffer, encoding='utf-8', errors='replace')

from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(REPO_ROOT, "users.db")
OUT_DIR = os.path.join(REPO_ROOT, "docs", "hlc_health")

TABLES = [
    "conversations", "group_members", "group_messages", "groups",
    "interaction_patterns", "knowledge_base", "messages",
    "project_docs", "safety_memory", "space_nodes",
    "task_feedback", "users",
]

def check():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    report = []
    report.append(f"# HLC 健康度报告 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # 1. 触发器检查
    cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_%_hlc'")
    triggers = [r[0] for r in cur.fetchall()]
    report.append(f"## 触发器")
    report.append(f"- 已安装: {len(triggers)} / {len(TABLES)}")
    if len(triggers) < len(TABLES):
        missing = [t for t in TABLES if f"trg_{t}_hlc" not in triggers]
        report.append(f"- ⚠️ 缺失: {missing}")
    report.append("")

    # 2. 各表 HLC 覆盖情况
    report.append(f"## 各表 HLC 覆盖")
    report.append("")
    report.append("| 表 | 总行数 | 有 HLC | 缺失 | n000 来源 | n001 来源 | 其他节点 |")
    report.append("|----|--------|--------|------|-----------|-----------|---------|")

    total_rows = 0
    total_missing = 0
    for table in TABLES:
        cur.execute(f"SELECT COUNT(*) as c FROM {table}")
        total = cur.fetchone()["c"]
        cur.execute(f"SELECT COUNT(*) as c FROM {table} WHERE hlc_ts IS NULL OR hlc_ts = ''")
        missing = cur.fetchone()["c"]
        cur.execute(f"SELECT COUNT(*) as c FROM {table} WHERE origin_node = 'n000'")
        n000 = cur.fetchone()["c"]
        cur.execute(f"SELECT COUNT(*) as c FROM {table} WHERE origin_node = 'n001'")
        n001 = cur.fetchone()["c"]
        other = total - missing - n000 - n001
        total_rows += total
        total_missing += missing

        flag = " ⚠️" if missing > 0 else ""
        report.append(f"| {table} | {total} | {total-missing} | {missing}{flag} | {n000} | {n001} | {other} |")

    report.append("")
    report.append(f"**总计**: {total_rows} 行，缺失 HLC {total_missing} 行")
    report.append("")

    # 3. 单调性检查（最近 1000 条 messages）
    report.append(f"## 单调性检查（messages 最近 1000 条）")
    cur.execute("SELECT id, hlc_ts FROM messages WHERE hlc_ts IS NOT NULL ORDER BY id DESC LIMIT 1000")
    rows = cur.fetchall()
    inversions = 0
    for i in range(1, len(rows)):
        prev_hlc = rows[i]["hlc_ts"]
        curr_hlc = rows[i-1]["hlc_ts"]
        if prev_hlc and curr_hlc and prev_hlc > curr_hlc:
            inversions += 1
    report.append(f"- 检查: {len(rows)} 条")
    report.append(f"- 逆序: {inversions} 条 {'✅' if inversions == 0 else '⚠️'}")
    report.append("")

    # 4. HLC 生成器状态
    report.append(f"## HLC 生成器状态")
    cur.execute("SELECT * FROM hlc_state")
    states = cur.fetchall()
    if states:
        for s in states:
            report.append(f"- 节点 {s['node_id']}: last_physical={s['last_physical']} counter={s['last_counter']} at={s['updated_at']}")
    else:
        report.append("- ⚠️ hlc_state 表为空")
    report.append("")

    # 5. 结论
    ok = (len(triggers) == len(TABLES)) and (total_missing == 0) and (inversions == 0) and bool(states)
    report.append(f"## 结论")
    report.append(f"- 整体: {'✅ 健康' if ok else '⚠️ 有问题'}")
    if not ok:
        if len(triggers) < len(TABLES):
            report.append(f"  - 触发器缺失 {len(TABLES) - len(triggers)} 个")
        if total_missing > 0:
            report.append(f"  - {total_missing} 行缺 HLC")
        if inversions > 0:
            report.append(f"  - {inversions} 处逆序")
        if not states:
            report.append(f"  - hlc_state 为空")

    conn.close()

    # 输出
    text = "\n".join(report)
    print(text)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_file = os.path.join(OUT_DIR, f"{datetime.now().strftime('%Y%m%d')}.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n[hlc_health] 已写入 {out_file}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(check())
