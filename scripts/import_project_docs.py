# scripts/import_project_docs.py
"""投喂一份项目文档到项目库

用法:
    python scripts/import_project_docs.py docs/xxx.md v0.17.0
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services import project_service


TASK_PREFIX = 'task__'
RULE_PREFIX = 'cur_pit_'


def _iter_active_md():
    """扫描 docs/tasks/active 下所有 .md，返回 [(source_file, abs_path)]"""
    import os
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'tasks', 'active')
    result = []
    if not os.path.isdir(base):
        return result
    for root, _, files in os.walk(base):
        for fn in files:
            if not fn.endswith('.md'):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, base).replace(os.sep, '__')
            result.append((TASK_PREFIX + rel, full))
    return result


def sync_from_active():
    """以 active/ 为准，对齐 project_docs 的 task__ 分片"""
    from core.db import db_cursor

    active = _iter_active_md()
    active_map = dict(active)

    with db_cursor() as cur:
        cur.execute("SELECT DISTINCT source_file FROM project_docs WHERE source_file LIKE ?", (TASK_PREFIX + '%',))
        db_files = {r[0] for r in cur.fetchall()}

    to_delete = db_files - set(active_map.keys())
    for f in to_delete:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM project_docs WHERE source_file=?", (f,))
            cur.execute("DELETE FROM project_docs_meta WHERE source_file=?", (f,))
        print("[sync] 删除过期分片: {}".format(f))

    for source, full in active_map.items():
        with open(full, 'r', encoding='utf-8') as fh:
            raw = fh.read()
        n = project_service.import_document(source, 'active', raw, allow_system=True)
        print("[sync] 投喂 {}: {} 分片".format(source, n))


def sync_rules_from_active():
    """以 active/rules/*.json 为准，对齐 cognitive_rules 的 cur_pit_ 规则"""
    import os
    import json
    from core.db import db_cursor

    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'tasks', 'active', 'rules')
    active_rules = {}
    if os.path.isdir(base):
        for fn in os.listdir(base):
            if not fn.endswith('.json'):
                continue
            full = os.path.join(base, fn)
            try:
                with open(full, 'r', encoding='utf-8') as fh:
                    rule = json.load(fh)
                active_rules[rule['rule_id']] = rule
            except Exception as e:
                print("[sync] 跳过坏规则 {}: {}".format(fn, e))

    with db_cursor() as cur:
        cur.execute("SELECT rule_id FROM cognitive_rules WHERE rule_id LIKE ?", (RULE_PREFIX + '%',))
        db_rules = {r[0] for r in cur.fetchall()}

    to_delete = db_rules - set(active_rules.keys())
    for rid in to_delete:
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM cognitive_rules WHERE rule_id=?", (rid,))
        print("[sync] 删除过期规则: {}".format(rid))

    for rid, rule in active_rules.items():
        with db_cursor(commit=True) as cur:
            _now = __import__('datetime').datetime.now().isoformat()
            cur.execute(
                "INSERT OR REPLACE INTO cognitive_rules (rule_id, domain_main, domain_sub, rule_content, trigger_context, confidence, status, created_at, updated_at) VALUES (?,?,?,?,?,?,'active',?,?)",
                (rule['rule_id'], rule.get('domain_main',''), rule.get('domain_sub',''), rule.get('rule_content',''), json.dumps(rule.get('trigger_context',{})), rule.get('confidence',1.0), _now, _now)
            )
        print("[sync] 投喂规则: {}".format(rid))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] in ('--sync', 'sync'):
        sync_from_active()
        sync_rules_from_active()
        print("[sync] 完成")
        return 0

    if len(sys.argv) < 2:
        print("用法: python scripts/import_project_docs.py <文件路径> [版本号]")
        return 1

    file_path = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else "unknown"

    if not os.path.exists(file_path):
        print(f"[错误] 文件不存在: {file_path}")
        return 1

    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    source_file = os.path.basename(file_path)
    n = project_service.import_document(source_file, version, raw, allow_system=True)
    print(f"[完成] 导入 {n} 个分片")
    return 0


if __name__ == "__main__":
    exit(main())