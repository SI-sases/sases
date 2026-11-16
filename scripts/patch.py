# -*- coding: utf-8 -*-
"""SASES 补丁集合：所有代码修复注册在这里，可重放、幂等、可审计。

用法：
  python scripts/patch.py --list                 列出所有补丁及状态
  python scripts/patch.py --name ctx_v2          跑指定补丁
  python scripts/patch.py --all                  跑所有未应用的补丁（重装环境用）
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
NL = chr(10)
PATCHES = {}


def register(name):
    def deco(fn):
        PATCHES[name] = fn
        return fn
    return deco


def _try_compile(*paths):
    import py_compile
    for p in paths:
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            print('  SYNTAX_ERROR {}: {}'.format(p, e))
            return False
    return True


# ==================== 今晚的修复清单 ====================

@register('model_call_empty')
def patch_model_call_empty():
    """model_call.py 空 config 明确报错，不静默走 env"""
    p = ROOT / 'core/services/message/model_call.py'
    s = p.read_text(encoding='utf-8')
    if '未找到模型配置，请先在' in s:
        print('  ALREADY_DONE')
        return True
    old = '        if model_config["model_type"] == "api":'
    new = (
        '        if not model_config:' + NL +
        '            raise Exception("未找到模型配置，请先在「我的 → 模型管理」绑定 API Key")' + NL +
        '        if model_config["model_type"] == "api":'
    )
    if old not in s:
        print('  OLD_NOT_FOUND')
        return False
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    print('  PATCHED')
    return _try_compile(p)


@register('direct_no_hijack')
def patch_direct_no_hijack():
    """direct_channel.py 明确指定工具时不劫持"""
    p = ROOT / 'core/services/message/direct_channel.py'
    s = p.read_text(encoding='utf-8')
    if '_explicit_tool_call' in s:
        print('  ALREADY_DONE')
        return True
    anchor = '    if not _should_try_direct(content):'
    idx = s.find(anchor)
    if idx < 0:
        print('  ANCHOR_NOT_FOUND')
        return False
    inject = (
        '    _explicit_tool_call = (chr(116)+chr(121)+chr(112)+chr(101)+chr(61)+chr(104)+chr(97)+chr(114)+chr(110)+chr(101)+chr(115)+chr(115), chr(109)+chr(111)+chr(100)+chr(117)+chr(108)+chr(101)+chr(95)+chr(105)+chr(100)+chr(61))' + NL +
        '    if any(kw in content for kw in _explicit_tool_call):' + NL +
        '        return False, ""' + NL
    )
    s = s[:idx] + inject + s[idx:]
    p.write_text(s, encoding='utf-8')
    print('  PATCHED')
    return _try_compile(p)


@register('grep_skip_dirs')
def patch_grep_skip_dirs():
    """grep_code 排除 build_portable、python312 等"""
    p = ROOT / 'harness_modules/grep_code/main.py'
    s = p.read_text(encoding='utf-8')
    if 'build_portable' in s:
        print('  ALREADY_DONE')
        return True
    old = "SKIP_DIRS = ('venv312', 'venv', 'node_modules', '.git', '__pycache__', '.backups', 'archive', 'training_data', 'seeds')"
    new = "SKIP_DIRS = ('venv312', 'venv', 'node_modules', '.git', '__pycache__', '.backups', 'archive', 'training_data', 'seeds', 'build_portable', 'python312', 'dist', 'release', 'logs')"
    if old not in s:
        print('  OLD_NOT_FOUND')
        return False
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    print('  PATCHED')
    return _try_compile(p)


@register('ctx_task_context')
def patch_ctx_task_context():
    """context_service.py 强制注入 task_context + 历史截断"""
    p = ROOT / 'core/services/context_service.py'
    s = p.read_text(encoding='utf-8')
    if 'task_context recall failed' in s and '_hist_limit = 2 if parts else 10' in s:
        print('  ALREADY_DONE')
        return True

    if 'task_context recall failed' not in s:
        old = '    parts = []' + NL + NL + '    hist_lines = []'
        new = (
            '    parts = []' + NL + NL +
            '    try:' + NL +
            "        for _tc in memory_service.recall_by_type(user_id, 'task_context', top_k=2):" + NL +
            "            parts.append('【当前任务（必读）】' + NL + str(_tc.get('content', '')))" + NL +
            '    except Exception as _tc_e:' + NL +
            "        print('[context] task_context recall failed: ' + str(_tc_e))" + NL + NL +
            '    hist_lines = []'
        )
        if old not in s:
            print('  [A] OLD_NOT_FOUND')
            return False
        s = s.replace(old, new, 1)
        print('  [A] task_context inject PATCHED')

    if '_hist_limit = 2 if parts else 10' not in s:
        old_b = (
            '    hist_lines = []' + NL +
            '    try:' + NL +
            '        with db_cursor() as cur:' + NL +
            "            cur.execute('SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 10', (conversation_id,))"
        )
        new_b = (
            '    hist_lines = []' + NL +
            '    _hist_limit = 2 if parts else 10' + NL +
            '    try:' + NL +
            '        with db_cursor() as cur:' + NL +
            "            cur.execute('SELECT sender, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?', (conversation_id, _hist_limit))"
        )
        if old_b not in s:
            print('  [B] OLD_NOT_FOUND')
            return False
        s = s.replace(old_b, new_b, 1)
        print('  [B] hist truncate PATCHED')

    p.write_text(s, encoding='utf-8')
    return _try_compile(p)


@register('send_proj_high_ctx')
def patch_send_proj_high_ctx():
    """send.py 项目库高分时也走 build_enriched_prompt"""
    p = ROOT / 'core/services/message/send.py'
    s = p.read_text(encoding='utf-8')
    if '_ctx_hi.build_enriched_prompt' in s:
        print('  ALREADY_DONE')
        return True
    old = (
        '                            project_text = project_service.format_chunks_for_prompt(chunks)' + NL +
        '                            enriched_query = project_text + "\\n\\n【用户问题】\\n" + content' + NL +
        '                            print(f"[message] 项目库高分命中 {_top:.3f}")'
    )
    new = (
        '                            project_text = project_service.format_chunks_for_prompt(chunks)' + NL +
        '                            from .. import context_service as _ctx_hi' + NL +
        '                            enriched_query = _ctx_hi.build_enriched_prompt(user_id, conversation_id, content, project_text)' + NL +
        '                            print(f"[message] 项目库高分命中 {_top:.3f}(含 task_context)")'
    )
    if old not in s:
        print('  OLD_NOT_FOUND')
        return False
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    print('  PATCHED')
    return _try_compile(p)


@register('send_is_sases_chat')
def patch_send_is_sases_chat():
    """send.py 所有智能体都注入上下文"""
    p = ROOT / 'core/services/message/send.py'
    s = p.read_text(encoding='utf-8')
    if '_is_sases_chat = True' in s:
        print('  ALREADY_DONE')
        return True
    lines = s.split(chr(10))
    hit = 0
    for i, l in enumerate(lines):
        if '_is_sases_chat =' in l and "'sases'" in l:
            lines[i] = '            _is_sases_chat = True  # inject'
            hit += 1
    if hit == 0:
        print('  NOT_FOUND')
        return False
    p.write_text(chr(10).join(lines), encoding='utf-8')
    print('  PATCHED ({})'.format(hit))
    return _try_compile(p)


@register('run_python_backup')
def patch_run_python_backup():
    """run_python 写入前自动备份到 .backups/"""
    p = ROOT / 'harness_modules/run_python/main.py'
    s = p.read_text(encoding='utf-8')
    if '_auto_backup' in s:
        print('  ALREADY_DONE')
        return True
    lines = s.split(chr(10))
    backup_def = [
        "    'def _auto_backup(safe, abs_p):',",
        "    '    if not _real_os.path.exists(abs_p):',",
        "    '        return',",
        "    '    try:',",
        "    \"        bak_dir = _real_os.path.join(_REPO_ROOT, '.backups')\",",
        "    '        _real_os.makedirs(bak_dir, exist_ok=True)',",
        "    \"        _safe = safe.replace('/', '__').replace(chr(92), '__')\",",
        "    '        from datetime import datetime as _dt',",
        "    \"        bak_path = _real_os.path.join(bak_dir, _safe + '.' + _dt.now().strftime('%Y%m%d_%H%M%S_%f') + '.bak')\",",
        "    \"        with _real_open(abs_p, 'rb') as _f:\",",
        "    '            _c = _f.read()',",
        "    \"        with _real_open(bak_path, 'wb') as _f:\",",
        "    '            _f.write(_c)',",
        "    '    except Exception:',",
        "    '        pass',",
    ]
    target_wf_def = "    'def write_file(path, content):',"
    found = False
    for i, l in enumerate(lines):
        if l == target_wf_def:
            lines[i:i] = backup_def
            found = True
            break
    if not found:
        print('  WF_DEF_NOT_FOUND')
        return False

    found = False
    for i, l in enumerate(lines):
        if 'with _real_open(abs_p,' in l and "'w'" in l:
            lines.insert(i, "    '    _auto_backup(safe, abs_p)',")
            found = True
            break
    if not found:
        print('  WF_CALL_NOT_FOUND')
        return False

    target_open = "    '    return _real_open(abs_p, mode, *args, **kwargs)',"
    found = False
    for i, l in enumerate(lines):
        if l == target_open:
            lines.insert(i, "    '    if any(_c in mode for _c in (chr(119), chr(97), chr(120), chr(43))):',")
            lines.insert(i+1, "    '        _auto_backup(safe, abs_p)',")
            found = True
            break
    if not found:
        print('  OPEN_NOT_FOUND')
        return False

    p.write_text(chr(10).join(lines), encoding='utf-8')
    print('  PATCHED')
    return _try_compile(p)

@register('p1_import_sync')
def patch_p1_import_sync():
    """import_project_docs.py 加 --sync：扫 active/ 全量对齐 project_docs + cognitive_rules"""
    p = ROOT / 'scripts/import_project_docs.py'
    s = p.read_text(encoding='utf-8')
    if 'def sync_from_active' in s:
        print('  ALREADY_DONE')
        return True

    anchor = 'def main():'
    if anchor not in s:
        print('  ANCHOR_NOT_FOUND')
        return False

    sync_code = '''TASK_PREFIX = 'task__'
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
            cur.execute(
                "INSERT OR REPLACE INTO cognitive_rules (rule_id, domain_main, domain_sub, rule_type, rule_content, trigger_context, confidence, source_type, status) VALUES (?,?,?,?,?,?,?,?,'active')",
                (rule['rule_id'], rule.get('domain_main',''), rule.get('domain_sub',''), rule.get('rule_type','pitfall'), rule.get('rule_content',''), json.dumps(rule.get('trigger_context',{})), rule.get('confidence',1.0), rule.get('source_type','seed'))
            )
        print("[sync] 投喂规则: {}".format(rid))


'''

    s = s.replace(anchor, sync_code + anchor, 1)

    main_anchor = '''    if len(sys.argv) < 2:
        print("'''
    if main_anchor not in s:
        print('  MAIN_ANCHOR_NOT_FOUND')
        return False

    sync_branch = '''    if len(sys.argv) >= 2 and sys.argv[1] in ('--sync', 'sync'):
        sync_from_active()
        sync_rules_from_active()
        print("[sync] 完成")
        return 0

'''
    s = s.replace(main_anchor, sync_branch + main_anchor, 1)

    p.write_text(s, encoding='utf-8')
    print('  PATCHED')
    return _try_compile(p)

@register('prompts_cleanup_A')
def patch_prompts_cleanup_A():
    """A批：清空壳 + 修明确失效 + 加归档纪律"""
    p = ROOT / 'core/services/swarm/prompts.py'
    s = p.read_text(encoding='utf-8')

    if '【归档纪律（v0.41.0' in s:
        print('  ALREADY_DONE')
        return True

    changes = []

    # 1. 删空壳【执行优先级铁律】
    old1 = '【执行优先级铁律】' + NL + NL
    if old1 in s:
        s = s.replace(old1, '', 1)
        changes.append('del 执行优先级铁律')

    # 2. 删空壳【规则】
    old2 = '【规则】' + NL + '【工具优先级与 harness 铁律】'
    if old2 in s:
        s = s.replace(old2, '【工具优先级与 harness 铁律】', 1)
        changes.append('del 规则')

    # 3. 修孤立"整体覆写"行
    old3 = '    整体覆写: overwrite=true + new_content'
    new3 = '  - file_write: file_path + new_content；新建加 create_if_missing=true'
    if old3 in s:
        s = s.replace(old3, new3, 1)
        changes.append('fix 整体覆写')

    # 4. 修别名映射
    old4 = '都必须写成 module_id="写操作工具"'
    new4 = '都必须写成 module_id="file_write"'
    if old4 in s:
        s = s.replace(old4, new4, 1)
        changes.append('fix 别名映射')

    # 5. 修改文件指向三工具
    old5 = '· 改文件 → 写操作工具'
    new5 = '· 改文件 → file_write(整文件) / smart_edit(片段) / file_replace_range(行号)'
    if old5 in s:
        s = s.replace(old5, new5, 1)
        changes.append('fix 改文件三工具')

    # 6. 加归档纪律段（在【整理类任务约束】前插入）
    anchor6 = '【整理类任务约束（用户说"整理/归类/分类"时，必须遵守）】'
    if anchor6 in s:
        new6 = (
            '【归档纪律（v0.41.0，违反必回退）】' + NL +
            '- 任务完成后只输出 [SUMMARY]，绝不自动调用 archive_task.py' + NL +
            '- 用户明确说"执行归档"时，才调：python scripts/archive_task.py --task <任务名>' + NL +
            '- 归档前必须先跑 --dry-run，展示将移动的文件' + NL +
            '- 归档后自检 task_context 残留、task__ 分片残留必须为 0' + NL +
            '- 归档是用户的权利，不是三者的判断' + NL + NL +
            anchor6
        )
        s = s.replace(anchor6, new6, 1)
        changes.append('add 归档纪律')

    if not changes:
        print('  NO_CHANGES')
        return False

    print('  changes: ' + ', '.join(changes))
    p.write_text(s, encoding='utf-8')
    return _try_compile(p)


# ==================== 入口 ====================

@register('bootstrap_memory_backfill')
def patch_bootstrap_memory_backfill():
    """bootstrap.py 加 periodic_memory_backfill，每 30 分钟补齐 embedding"""
    p = ROOT / 'core/bootstrap.py'
    s = p.read_text(encoding='utf-8')
    if 'periodic_memory_backfill' in s:
        print('  ALREADY_DONE')
        return True

    # 锚点 A：函数定义插到 periodic_red_packet_expire 之后、@asynccontextmanager 之前
    anchor_a = '            await asyncio.sleep(3600)' + NL + NL + '@asynccontextmanager'
    if anchor_a not in s:
        print('  [A] ANCHOR_NOT_FOUND')
        return False

    func_def = (
        'async def periodic_memory_backfill():' + NL +
        '    """每 30 分钟补齐一次缺失的 embedding，防新写入踩坑。"""' + NL +
        '    await asyncio.sleep(60)' + NL +
        '    while True:' + NL +
        '        try:' + NL +
        '            from .services import memory_service' + NL +
        '            n = await asyncio.to_thread(memory_service.backfill_embeddings, 200)' + NL +
        '            if n > 0:' + NL +
        '                print("[memory-backfill] 补齐 {} 条".format(n))' + NL +
        '        except Exception as e:' + NL +
        '            print("[memory-backfill] 失败: {}".format(e))' + NL +
        '        await asyncio.sleep(1800)' + NL +
        NL
    )

    new_a = '            await asyncio.sleep(3600)' + NL + NL + NL + func_def + '@asynccontextmanager'
    s = s.replace(anchor_a, new_a, 1)
    print('  [A] func defined')

    # 锚点 B：注册
    anchor_b = '    _background_tasks.append(asyncio.create_task(periodic_hlc_health()))'
    if anchor_b not in s:
        print('  [B] ANCHOR_NOT_FOUND')
        return False
    new_b = anchor_b + NL + '    _background_tasks.append(asyncio.create_task(periodic_memory_backfill()))'
    s = s.replace(anchor_b, new_b, 1)
    print('  [B] registered')

    p.write_text(s, encoding='utf-8')
    return _try_compile(p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true', help='列出所有补丁')
    ap.add_argument('--name', help='跑指定补丁')
    ap.add_argument('--all', action='store_true', help='跑所有补丁（幂等，已应用的跳过）')
    args = ap.parse_args()

    if args.list:
        print('可用补丁：')
        for name, fn in PATCHES.items():
            print('  {:<24} {}'.format(name, (fn.__doc__ or '').strip().split(chr(10))[0]))
        return

    if args.all:
        ok_count = 0
        for name, fn in PATCHES.items():
            print('=== {} ==='.format(name))
            try:
                if fn():
                    ok_count += 1
            except Exception as e:
                print('  ERR', e)
        print()
        print('完成 {}/{}'.format(ok_count, len(PATCHES)))
        sys.exit(0 if ok_count == len(PATCHES) else 1)

    if not args.name:
        print('必须指定 --name 或 --all 或 --list')
        sys.exit(1)

    if args.name not in PATCHES:
        print('未知补丁: {}'.format(args.name))
        print('可用: {}'.format(list(PATCHES.keys())))
        sys.exit(1)

    print('=== {} ==='.format(args.name))
    ok = PATCHES[args.name]()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
