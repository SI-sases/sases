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
