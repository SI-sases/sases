# harness_modules/file_patch/main.py
"""
文件修改工具。支持三种模式：

模式1（精确片段替换）：
  参数: file_path, old_snippet, new_snippet, expected_count

模式2（锚点定位，推荐）：
  参数: file_path, anchor_pattern, position, new_content

模式3（创建/覆写文件，v2.1 新增）：
  参数: file_path, new_content, create_if_missing=true
  行为: 文件不存在或为空时，直接写入 new_content

【v2.3.0 权限】
  - 项目内允许目录：static/ / core/ / scripts/ / docs/ / harness_modules/
  - 外部允许目录：D:/ 全盘（用于多实例测试）
  - 禁止文件：users.db / .env / *.key / *.bin / *.pem / *.crt
  - 自我保护：file_patch 自身、executor_service.py
  - 自动备份到 .backups/
"""
import os
import difflib
from datetime import datetime

ALLOWED_DIRS = ("static/", "core/", "scripts/", "docs/", "harness_modules/", "data/", "logs/", "launcher/")
FORBIDDEN_EXT = {".db", ".key", ".bin", ".env", ".pem", ".crt", ".sqlite", ".sqlite3"}
FORBIDDEN_PARTS = {".env", "users.db", "secret_key", "api_key_encryption", ".backups"}
SELF_PROTECTED_FILES = {
    "harness_modules/file_patch/main.py",
    "harness_modules/file_patch/manifest.json",
    "core/services/executor_service.py",
}
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = ".backups"

# 非 C 盘全盘放开（C 盘受项目白名单限制）
import re as _re
_EXTERNAL_RE = _re.compile(r'^([A-Za-z]):/')


def _is_external_allowed(p: str) -> bool:
    """非 C 盘一律放行"""
    m = _EXTERNAL_RE.match(p)
    if not m:
        return False
    return m.group(1).upper() != 'C'


def _validate_path(file_path: str) -> str:
    if not file_path or not isinstance(file_path, str):
        raise ValueError("缺少 file_path 参数")
    p = file_path.replace("\\", "/").strip()

    _is_external = _is_external_allowed(p)

    # 项目内检查（外部白名单跳过）
    if not _is_external:
        if p.startswith("/") or (len(p) > 1 and p[1] == ":"):
            raise ValueError(f"禁止绝对路径: {file_path}")
        if ".." in p.split("/"):
            raise ValueError(f"禁止路径穿越: {file_path}")
        if not any(p.startswith(d) for d in ALLOWED_DIRS):
            allowed = " / ".join(ALLOWED_DIRS)
            raise ValueError(f"只允许修改以下目录：{allowed}，收到: {file_path}")

    # 敏感文件检查（对内外都生效）
    lower = p.lower()
    for part in FORBIDDEN_PARTS:
        if part in lower:
            raise ValueError(f"禁止修改敏感文件: {file_path}")
    ext = os.path.splitext(p)[1].lower()
    if ext in FORBIDDEN_EXT:
        raise ValueError(f"禁止修改 {ext} 类型文件")

    # 自我保护（只对项目内文件生效）
    if not _is_external and p in SELF_PROTECTED_FILES:
        raise ValueError(f"禁止修改受保护文件: {file_path}")

    return p


def _backup_before_write(abs_path, safe_path):
    try:
        if not os.path.exists(abs_path):
            return None
        # D 盘的备份放到 D 盘的同级 .backups
        _backup_dir = BACKUP_DIR
        if _is_external_allowed(safe_path.replace("\\", "/")):
            _backup_dir = os.path.join(os.path.dirname(abs_path), ".backups")
        os.makedirs(_backup_dir, exist_ok=True)
        safe_name = safe_path.replace("/", "__").replace("\\", "__")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = os.path.join(_backup_dir, f"{safe_name}.{timestamp}.bak")
        with open(abs_path, "r", encoding="utf-8") as src:
            content = src.read()
        with open(backup_path, "w", encoding="utf-8") as dst:
            dst.write(content)
        return backup_path
    except Exception as e:
        print(f"[file_patch] 备份失败: {e}")
        return None


def _mode_snippet(abs_path, safe_path, params):
    old_snippet = params.get("old_snippet", "")
    new_snippet = params.get("new_snippet", "")
    expected_count = params.get("expected_count", 1)

    if not old_snippet:
        raise ValueError("缺少 old_snippet 参数")
    if new_snippet is None:
        raise ValueError("缺少 new_snippet 参数")
    if not isinstance(expected_count, int) or expected_count < 1:
        raise ValueError("expected_count 必须是 >=1 的整数")

    with open(abs_path, "r", encoding="utf-8") as f:
        original = f.read()

    count = original.count(old_snippet)
    if count == 0:
        _cs = _find_similar_lines(original, old_snippet[:60])
        _h = chr(10) + '（无相似候选，请先 file_read 查看原文）'
        if _cs:
            _h = chr(10) + '最相似候选：' + chr(10)
            for _r, _ln, _tx in _cs:
                _h += '  行 ' + str(_ln) + ': ' + _tx + chr(10)
        raise ValueError(f"原片段在 {safe_path} 中未找到。建议改用锚点模式。" + _h)
    if count != expected_count:
        raise ValueError(f"原片段在 {safe_path} 中出现 {count} 次，期望 {expected_count} 次。")

    backup_path = _backup_before_write(abs_path, safe_path)
    new_content = original.replace(old_snippet, new_snippet)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return {
        "success": True, "mode": "snippet", "file_path": safe_path,
        "matches_replaced": count,
        "old_length": len(original), "new_length": len(new_content),
        "diff_bytes": len(new_content) - len(original),
        "backup": backup_path,
        "restart_required": safe_path.startswith("core/"),
    }


def _find_similar_lines(content, anchor, top_k=3):
    lines = content.split(chr(10))
    scored = []
    a = (anchor or '').strip()
    if not a:
        return []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        r = difflib.SequenceMatcher(None, a, s).ratio()
        if r > 0.4:
            scored.append((r, i + 1, s[:120]))
    scored.sort(reverse=True)
    return scored[:top_k]


def _mode_anchor(abs_path, safe_path, params):
    anchor = params.get("anchor_pattern", "")
    position = params.get("position", "after").lower()
    new_content = params.get("new_content", "")

    if not anchor:
        raise ValueError("缺少 anchor_pattern 参数")
    if position not in ("before", "after", "replace_line"):
        raise ValueError(f"position 必须是 before/after/replace_line，收到: {position}")
    if new_content is None:
        raise ValueError("缺少 new_content 参数")

    with open(abs_path, "r", encoding="utf-8") as f:
        original = f.read()

    lines = original.split("\n")
    matched_indices = [i for i, line in enumerate(lines) if anchor in line]

    if len(matched_indices) == 0:
        _cs = _find_similar_lines(original, anchor)
        _h = chr(10) + '（无相似候选，请先 file_read 查看原文）'
        if _cs:
            _h = chr(10) + '最相似候选：' + chr(10)
            for _r, _ln, _tx in _cs:
                _h += '  行 ' + str(_ln) + ': ' + _tx + chr(10)
            _h += '请从上述候选选一个作为 anchor_pattern。'
        raise ValueError(f"锚点 '{anchor}' 在 {safe_path} 中未找到任何匹配行" + _h)
    if len(matched_indices) > 1:
        raise ValueError(
            f"锚点 '{anchor}' 匹配到 {len(matched_indices)} 行，期望 1 行。"
            f"匹配行号：{[i+1 for i in matched_indices]}。请用更精确的锚点。"
        )

    idx = matched_indices[0]
    matched_line = lines[idx]
    backup_path = _backup_before_write(abs_path, safe_path)

    if position == "before":
        lines.insert(idx, new_content)
        action = f"在第 {idx+1} 行前插入"
    elif position == "after":
        lines.insert(idx + 1, new_content)
        action = f"在第 {idx+1} 行后插入"
    else:
        lines[idx] = new_content
        action = f"替换第 {idx+1} 行"

    new_text = "\n".join(lines)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    return {
        "success": True, "mode": "anchor", "file_path": safe_path,
        "anchor": anchor, "matched_line_number": idx + 1,
        "matched_line_preview": matched_line.strip()[:120],
        "position": position, "action": action,
        "old_length": len(original), "new_length": len(new_text),
        "diff_bytes": len(new_text) - len(original),
        "backup": backup_path,
        "restart_required": safe_path.startswith("core/"),
    }


def _mode_create(abs_path, safe_path, params):
    """模式3：创建或覆写文件（v2.1 新增）"""
    new_content = params.get("new_content", "")
    if not new_content:
        raise ValueError("创建/覆写文件时必须提供非空 new_content")

    existed = os.path.exists(abs_path)
    old_length = 0
    backup_path = None
    if existed:
        with open(abs_path, "r", encoding="utf-8") as f:
            old_length = len(f.read())
        backup_path = _backup_before_write(abs_path, safe_path)

    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return {
        "success": True,
        "mode": "create" if not existed else "overwrite",
        "file_path": safe_path,
        "old_length": old_length,
        "new_length": len(new_content),
        "backup": backup_path,
        "restart_required": safe_path.startswith("core/"),
    }




def _verify_syntax_after_write(abs_path, safe_path):
    """写入后自动验证语法。返回 (ok, error)"""
    import os as _os
    ext = _os.path.splitext(safe_path)[1].lower()
    if ext == '.py':
        try:
            import ast as _ast
            with open(abs_path, 'r', encoding='utf-8') as f:
                _ast.parse(f.read())
            return True, ''
        except SyntaxError as e:
            return False, 'line ' + str(e.lineno) + ': ' + str(e.msg)
        except Exception as e:
            return False, str(e)
    if ext == '.js':
        try:
            import subprocess as _sp
            r = _sp.run(['node', '--check', abs_path], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if r.returncode == 0:
                return True, ''
            return False, (r.stderr or '')[:400]
        except FileNotFoundError:
            return True, 'node not available'
        except Exception as e:
            return True, str(e)
    return True, ''

def _run_inner(params):
    file_path = params.get("file_path", "")
    safe_path = _validate_path(file_path)
    abs_path = os.path.abspath(safe_path)

    exists = os.path.exists(abs_path)
    is_empty = exists and os.path.getsize(abs_path) == 0
    create_if_missing = bool(params.get("create_if_missing", False))
    overwrite = bool(params.get("overwrite", False))

    # 显式 overwrite 优先
    if overwrite and exists:
        return _mode_create(abs_path, safe_path, params)

    # v2.4.0：文件不存在或为空 → 自动创建（不再要求 create_if_missing）
    if not exists or is_empty:
        return _mode_create(abs_path, safe_path, params)

    # 文件存在且非空 → 按参数路由
    if params.get("anchor_pattern"):
        return _mode_anchor(abs_path, safe_path, params)
    elif params.get("old_snippet"):
        return _mode_snippet(abs_path, safe_path, params)
    elif "new_content" in params:
        # v2.4.0：只传 new_content → 默认全量覆写
        return _mode_create(abs_path, safe_path, params)
    else:
        raise ValueError(
            "文件非空时必须提供：\n"
            "  - anchor_pattern（锚点模式，推荐）\n"
            "  - old_snippet（精确片段模式）\n"
            "  - 或 new_content（整体覆写）"
        )

def run(params):
    result = _run_inner(params)
    if isinstance(result, dict) and result.get('success'):
        fp = params.get('file_path') or ''
        if fp and (fp.endswith('.js') or fp.endswith('.py')):
            ok = True
            err = ''
            try:
                if fp.endswith('.py'):
                    import ast as _a
                    with open(fp, 'r', encoding='utf-8') as fh:
                        _a.parse(fh.read())
                else:
                    import subprocess as _sp
                    _r = _sp.run(['node', '--check', fp], capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
                    if _r.returncode != 0:
                        ok = False
                        err = (_r.stderr or '')[:300]
            except Exception as _e:
                ok = False
                err = str(_e)[:300]
                print('[fp-wrapper] verify fail:', _e)
            if not ok:
                bak = result.get('backup')
                if bak and os.path.exists(bak):
                    try:
                        import shutil as _sh
                        _sh.copy2(bak, fp)
                        result['rolled_back'] = True
                    except Exception:
                        result['rolled_back'] = False
                result['success'] = False
                result['syntax_error'] = err
                result['error'] = 'SYNTAX_ERROR: ' + err
    return result
