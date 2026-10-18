import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / ".backups"

FUNC_HEAD = re.compile(r"^\s*(async\s+function\s+\w+|function\s+\w+|(const|let|var)\s+\w+\s*=\s*(async\s*)?(function|\())")
ORPHAN_HEAD = re.compile(r"^\s*(try\s*\{|catch\s*\(|finally\s*\{|for\s*\(|while\s*\(|if\s*\()")


def _backup(p: Path):
    BACKUP_DIR.mkdir(exist_ok=True)
    b = BACKUP_DIR / (p.name + ".delete_block.bak")
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


def run(params):
    fp = params.get("file_path")
    start_pattern = params.get("start_pattern")
    end_marker = params.get("end_marker", "}")
    if not fp or not start_pattern:
        return {"ok": False, "error": "缺少 file_path 或 start_pattern"}

    p = Path(fp)
    if not p.is_absolute():
        p = ROOT / fp
    if not p.exists():
        return {"ok": False, "error": "文件不存在: %s" % fp}

    original = p.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    start_idx = -1
    for i, ln in enumerate(lines):
        if start_pattern in ln:
            start_idx = i
            break
    if start_idx < 0:
        return {"ok": False, "error": "未找到 start_pattern: %s" % start_pattern}

    end_idx = _find_block_end(lines, start_idx)
    if end_idx < 0:
        return {"ok": False, "error": "未找到匹配的结束括号"}

    before_ctx = "".join(lines[max(0, start_idx - 2):start_idx])
    after_ctx = "".join(lines[end_idx + 1:end_idx + 3])

    new_lines = lines[:start_idx] + lines[end_idx + 1:]
    new_text = "".join(new_lines)

    ob, cb = _brace_balance(new_text)
    if ob != cb:
        return {"ok": False, "error": "括号不平衡", "detail": "{数量: %d, }数量: %d" % (ob, cb)}

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

    bak = _backup(p)
    try:
        p.write_text(new_text, encoding="utf-8")
    except Exception as e:
        shutil.copy2(bak, p)
        return {"ok": False, "error": "写入失败已回滚: %s" % e}

    return {
        "ok": True,
        "file": str(p),
        "deleted_range": [start_idx + 1, end_idx + 1],
        "deleted_lines": end_idx - start_idx + 1,
        "before_context": before_ctx,
        "after_context": after_ctx,
        "brace_balance": {"open": ob, "close": cb},
    }
