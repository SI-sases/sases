import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / ".backups"

# v2.0: 恢复目录白名单
ALLOWED = ('static/', 'core/', 'scripts/', 'docs/', 'harness_modules/', 'launcher/', 'data/', 'logs/', 'tests/')
FORBIDDEN_EXT = {'.db', '.key', '.bin', '.env', '.pem', '.crt', '.sqlite', '.sqlite3'}

FUNC_HEAD = re.compile(r"^\s*(async\s+function\s+\w+|function\s+\w+|(const|let|var)\s+\w+\s*=\s*(async\s*)?(function|\())")
ORPHAN_HEAD = re.compile(r"^\s*(try\s*\{|catch\s*\(|finally\s*\{|for\s*\(|while\s*\(|if\s*\()")


def _validate_path(fp: str) -> str:
    p = fp.replace("\\", "/").strip()
    if not p or p.startswith("/") or (len(p) > 1 and p[1] == ":"):
        raise ValueError("禁止绝对路径: " + fp)
    if ".." in p.split("/"):
        raise ValueError("禁止路径穿越: " + fp)
    if not any(p.startswith(d) for d in ALLOWED):
        raise ValueError("只允许修改以下目录：%s，收到: %s" % (" / ".join(ALLOWED), fp))
    lower = p.lower()
    for part in ("users.db", ".env", "secret_key", "api_key_encryption"):
        if part in lower:
            raise ValueError("禁止修改敏感文件: " + fp)
    ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
    if "." + ext in FORBIDDEN_EXT:
        raise ValueError("禁止修改 %s 类型文件" % ext)
    return p


def _backup(p: Path):
    BACKUP_DIR.mkdir(exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    b = BACKUP_DIR / (p.name + ".delete_block." + ts + ".bak")
    shutil.copy2(p, b)
    return b


def _brace_balance(text: str):
    return text.count("{"), text.count("}")


def _find_block_end(lines, start_idx):
    depth = 0
    started = False
    for i in range(start_idx, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
        if started and depth <= 0:
            return i
    return -1


def _syntax_check(p: Path):
    """返回 (ok, error)。语法错误时调用方应回滚。"""
    ext = p.suffix.lower()
    try:
        if ext == ".py":
            import ast
            ast.parse(p.read_text(encoding="utf-8"))
            return True, ""
        if ext in (".js", ".mjs"):
            r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                return True, ""
            return False, (r.stderr or "")[:400]
    except FileNotFoundError:
        return True, "node not available"
    except Exception as e:
        return False, str(e)[:400]
    return True, ""


def run(params):
    fp = params.get("file_path")
    start_pattern = params.get("start_pattern")
    end_marker = params.get("end_marker", "}")
    replace_with = params.get("replace_with", "")
    dry_run = params.get("dry_run", False)
    if not fp or not start_pattern:
        return {"ok": False, "error": "缺少 file_path 或 start_pattern"}

    # 1. 路径校验
    try:
        safe_fp = _validate_path(fp)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    p = Path(safe_fp)
    if not p.is_absolute():
        p = ROOT / safe_fp
    if not p.exists():
        return {"ok": False, "error": "文件不存在: %s" % fp}

    original = p.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    # 2. 定位起始行
    start_idx = -1
    for i, ln in enumerate(lines):
        if start_pattern in ln:
            start_idx = i
            break
    if start_idx < 0:
        return {"ok": False, "error": "未找到 start_pattern: %s" % start_pattern}

    # 3. 括号计数找结束行
    end_idx = _find_block_end(lines, start_idx)
    if end_idx < 0:
        return {"ok": False, "error": "未找到匹配的结束括号"}

    before_ctx = "".join(lines[max(0, start_idx - 2):start_idx])
    after_ctx = "".join(lines[end_idx + 1:end_idx + 3])

    # v1.4: dry_run 模式——只返回要删除的内容，不实际删除
    if dry_run:
        _block = "".join(lines[start_idx:end_idx + 1])
        return {
            "ok": True,
            "dry_run": True,
            "file": str(p),
            "deleted_range": [start_idx + 1, end_idx + 1],
            "deleted_lines": end_idx - start_idx + 1,
            "block": _block,
            "before_context": before_ctx,
            "after_context": after_ctx,
        }


    # 4. 删除
    new_lines = lines[:start_idx]
    if replace_with:
        new_lines.append(replace_with.rstrip("\n") + "\n")
    new_lines += lines[end_idx + 1:]
    new_text = "".join(new_lines)

    # 5. 括号平衡检查
    ob, cb = _brace_balance(new_text)
    if ob != cb:
        return {"ok": False, "error": "括号不平衡", "detail": "{数量: %d, }数量: %d" % (ob, cb)}

    # 6. 孤儿块检测（只看删除位置后紧邻的第一个非空行）
    orphan = None
    for j in range(start_idx, min(start_idx + 5, len(new_lines))):
        ln = new_lines[j]
        if not ln.strip():
            continue
        if FUNC_HEAD.match(ln):
            break
        if ORPHAN_HEAD.match(ln):
            orphan = "行%d: %s" % (j + 1, ln.strip())
            break
        break
    if orphan:
        return {"ok": False, "error": "检测到孤立控制块", "detail": orphan}

    # 7. 备份
    bak = _backup(p)

    # 8. 写入
    try:
        p.write_text(new_text, encoding="utf-8")
    except Exception as e:
        shutil.copy2(bak, p)
        return {"ok": False, "error": "写入失败已回滚: %s" % e}

    # 9. 语法检查 + 失败回滚
    ok, err = _syntax_check(p)
    if not ok:
        shutil.copy2(bak, p)
        return {"ok": False, "error": "语法错误已回滚: " + err, "backup": str(bak)}

    return {
        "ok": True,
        "file": str(p),
        "deleted_range": [start_idx + 1, end_idx + 1],
        "deleted_lines": end_idx - start_idx + 1,
        "before_context": before_ctx,
        "after_context": after_ctx,
        "brace_balance": {"open": ob, "close": cb},
        "backup": str(bak),
    }
