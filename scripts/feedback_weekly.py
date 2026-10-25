"""SASES 反馈周报生成器

用法：
    python scripts/feedback_weekly.py              # 默认最近 7 天
    python scripts/feedback_weekly.py 14           # 最近 14 天
    python scripts/feedback_weekly.py 7 --out docs/feedback_weekly.md

输出：
    - 控制台打印摘要
    - 可选写入 markdown 文件
"""
import sys
import os
import json
import sqlite3
from datetime import datetime, timedelta

DB = "users.db"


def _stats(cur, since, until=None):
    sql = "SELECT rating, COUNT(*) as cnt FROM task_feedback WHERE created_at >= ?"
    params = [since]
    if until:
        sql += " AND created_at < ?"
        params.append(until)
    sql += " GROUP BY rating"
    cur.execute(sql, params)
    out = {"up": 0, "down": 0, "neutral": 0, "silent": 0}
    for r in cur.fetchall():
        key = r[0] or "unknown"
        out[key] = r[1]
    return out


def _type_stats(cur, since):
    cur.execute("""
        SELECT feedback_type, COUNT(*) FROM task_feedback
        WHERE created_at >= ? GROUP BY feedback_type
    """, (since,))
    return dict(cur.fetchall())


def _reason_stats(cur, since):
    cur.execute("""
        SELECT reason_tag, COUNT(*) FROM task_feedback
        WHERE created_at >= ? AND reason_tag IS NOT NULL
        GROUP BY reason_tag ORDER BY COUNT(*) DESC
    """, (since,))
    return cur.fetchall()


def _top_down_tasks(cur, since, limit=10):
    cur.execute("""
        SELECT task_id, reason_tag, task_snapshot FROM task_feedback
        WHERE created_at >= ? AND rating = 'down' AND is_latest = 1
        ORDER BY id DESC LIMIT ?
    """, (since, limit))
    rows = cur.fetchall()
    out = []
    for r in rows:
        try:
            snap = json.loads(r["task_snapshot"] or "{}")
            ui = (snap.get("user_input") or "")[:60]
        except Exception:
            ui = ""
        out.append({
            "task_id": r["task_id"],
            "reason_tag": r["reason_tag"],
            "user_input": ui,
        })
    return out


def _rate(stats):
    total = sum(stats.values())
    if total == 0:
        return 0.0
    return stats.get("down", 0) / total * 100


def main():
    days = 7
    out_file = None
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        if i + 1 < len(sys.argv):
            out_file = sys.argv[i + 1]

    now = datetime.now()
    since = (now - timedelta(days=days)).isoformat()
    prev_since = (now - timedelta(days=days * 2)).isoformat()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur_stats = _stats(cur, since)
    prev_stats = _stats(cur, prev_since, since)
    total_cur = sum(cur_stats.values())
    cur_down_rate = _rate(cur_stats)
    prev_down_rate = _rate(prev_stats)

    lines = []
    lines.append(f"=== SASES 反馈周报（{days} 天） ===")
    lines.append(f"生成时间：{now.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"本期反馈：{total_cur} 条")
    lines.append(f"  👍 {cur_stats.get('up', 0)}  👎 {cur_stats.get('down', 0)}  🤷 {cur_stats.get('neutral', 0)}  🔇 {cur_stats.get('silent', 0)}")
    lines.append("")

    type_stats = _type_stats(cur, since)
    if type_stats:
        lines.append("反馈类型：")
        for t, c in type_stats.items():
            lines.append(f"  {t}: {c}")
        lines.append("")

    reasons = _reason_stats(cur, since)
    if reasons:
        lines.append("👎 归因分布：")
        for tag, cnt in reasons:
            lines.append(f"  {tag:22s} {cnt} 条")
    else:
        lines.append("👎 归因：无")
    lines.append("")

    downs = _top_down_tasks(cur, since, 10)
    if downs:
        lines.append("近期 👎 任务（前 10）：")
        for r in downs:
            lines.append(f"  {r['task_id']}  [{r['reason_tag'] or '无归因'}]  {r['user_input']}")
    lines.append("")

    arrow = "→"
    if cur_down_rate > prev_down_rate + 3:
        arrow = "↑ 需警惕"
    elif cur_down_rate < prev_down_rate - 3:
        arrow = "↓ 改善"
    lines.append(f"👎 比率趋势：{prev_down_rate:.1f}% → {cur_down_rate:.1f}%  {arrow}")

    text = "\n".join(lines)
    print(text)

    # v0.40.1: 默认写入 docs/feedback_weekly/YYYYMMDD.md，同时维护 latest.md
    if not out_file:
        _archive_dir = os.path.join("docs", "feedback_weekly")
        os.makedirs(_archive_dir, exist_ok=True)
        _dated = os.path.join(_archive_dir, now.strftime("%Y%m%d") + ".md")
        _latest = os.path.join(_archive_dir, "latest.md")
        with open(_dated, "w", encoding="utf-8") as f:
            f.write(text)
        with open(_latest, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n已写入：{_dated}")
        print(f"最新快照：{_latest}")
        # 清理 90 天前的旧周报
        try:
            import glob as _g
            _cutoff = (now - timedelta(days=90)).strftime("%Y%m%d")
            for _f in _g.glob(os.path.join(_archive_dir, "*.md")):
                _base = os.path.basename(_f).replace(".md", "")
                if _base == "latest":
                    continue
                if _base < _cutoff:
                    os.remove(_f)
                    print(f"清理旧周报：{_f}")
        except Exception as e:
            print(f"清理旧周报失败: {e}")
    else:
        _d = os.path.dirname(out_file)
        if _d:
            os.makedirs(_d, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n已写入：{out_file}")


if __name__ == "__main__":
    main()