import json
import os
import shutil
import ast
import subprocess
from datetime import datetime

ALLOWED = ("static/", "core/", "scripts/", "docs/", "harness_modules/", "data/", "launcher/")
BACKUP_DIR = ".backups"


def _validate_path(path):
    p = path.replace("\\", "/")
    if p.startswith("/") or ":" in p:
        raise ValueError("禁止绝对路径: " + path)
    if not any(p.startswith(a) for a in ALLOWED):
        raise ValueError("路径不在允许目录: " + path)
    if ".." in p.split("/"):
        raise ValueError("禁止路径穿越: " + path)
    return p


def _backup(path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dst = os.path.join(BACKUP_DIR, os.path.basename(path) + "." + ts + ".bak")
    shutil.copy2(path, dst)
    return dst


def _syntax_ok(path):
    if path.endswith(".py"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            return True, ""
        except SyntaxError as e:
            return False, str(e)
    if path.endswith(".js"):
        try:
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True, timeout=15)
            return (r.returncode == 0), (r.stderr or "")
        except Exception as e:
            return False, str(e)
    return True, ""


def _find_unique(lines, pattern):
    hits = [i + 1 for i, ln in enumerate(lines) if pattern in ln]
    return hits


def run(params):
    result = {
        "success": False,
        "new_file": params.get("new_file"),
        "new_file_lines": 0,
        "deleted_range": None,
        "main_file_syntax_ok": False,
        "new_file_syntax_ok": False,
        "error": None,
    }
    src = None
    newf = None
    src_backup = None
    new_created = False
    try:
        src = _validate_path(params["source_file"])
        newf = _validate_path(params["new_file"])
        start_pattern = params["start_pattern"]
        end_pattern = params["end_pattern"]
        import_anchor = params.get("import_anchor") or ""
        replace_with = params.get("delete_replace_with") or ""

        if not os.path.exists(src):
            raise ValueError("源文件不存在: " + src)
        if os.path.exists(newf):
            raise ValueError("新文件已存在: " + newf)

        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines(keepends=True)

        s_hits = _find_unique(lines, start_pattern)
        e_hits = _find_unique(lines, end_pattern)
        if len(s_hits) != 1:
            raise ValueError("start_pattern 匹配 %d 处，必须唯一" % len(s_hits))
        if len(e_hits) != 1:
            raise ValueError("end_pattern 匹配 %d 处，必须唯一" % len(e_hits))
        start = s_hits[0]
        end = e_hits[0]
        if start >= end:
            raise ValueError("start(%d) 必须小于 end(%d)" % (start, end))

        block = lines[start - 1:end - 1]
        if not block:
            raise ValueError("切片为空")

        non_empty = [ln.rstrip() for ln in block if ln.strip()]
        if not non_empty or not non_empty[-1].endswith("};"):
            raise ValueError("切片最后一个非空行不是 };")
        if any(end_pattern in ln for ln in block):
            raise ValueError("切片包含 end_pattern")
        if not any(start_pattern in ln for ln in block):
            raise ValueError("切片不包含 start_pattern")

        src_backup = _backup(src)

        os.makedirs(os.path.dirname(newf) or ".", exist_ok=True)
        with open(newf, "w", encoding="utf-8") as f:
            f.writelines(block)
        new_created = True
        result["new_file_lines"] = len(block)

        ok, err = _syntax_ok(newf)
        result["new_file_syntax_ok"] = ok
        if not ok:
            raise ValueError("新文件语法错误: " + err)

        if import_anchor:
            a_hits = _find_unique(lines, import_anchor)
            if len(a_hits) != 1:
                raise ValueError("import_anchor 匹配 %d 处，必须唯一" % len(a_hits))
            base = os.path.basename(newf)
            imp_line = "import './" + base + "';\n"
            lines.insert(a_hits[0], imp_line)
            with open(src, "w", encoding="utf-8") as f:
                f.writelines(lines)
            ok, err = _syntax_ok(src)
            result["main_file_syntax_ok"] = ok
            if not ok:
                raise ValueError("源文件加 import 后语法错误: " + err)
            start += 1
            end += 1

        del lines[start - 1:end - 1]
        rep = replace_with
        if rep and not rep.endswith("\n"):
            rep += "\n"
        lines.insert(start - 1, rep)
        with open(src, "w", encoding="utf-8") as f:
            f.writelines(lines)

        ok, err = _syntax_ok(src)
        result["main_file_syntax_ok"] = ok
        if not ok:
            raise ValueError("源文件删除后语法错误: " + err)

        result["deleted_range"] = [start, end - 1]
        result["success"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        if new_created and newf and os.path.exists(newf):
            try:
                os.remove(newf)
            except Exception:
                pass
        if src_backup and src and os.path.exists(src_backup):
            try:
                shutil.copy2(src_backup, src)
            except Exception:
                pass
        return result
