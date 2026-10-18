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
    if p.startswith("/") or (len(p) > 1 and p[1] == ":"):
        raise ValueError("禁止绝对路径: " + path)
    if not any(p.startswith(a) for a in ALLOWED):
        raise ValueError("路径不在允许目录: " + path)
    if ".." in p.split("/"):
        raise ValueError("禁止路径穿越: " + path)
    return p


def _backup(path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = path.replace("\\", "/").replace("/", "__")
    dst = os.path.join(BACKUP_DIR, safe_name + "." + ts + ".bak")
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
            r = subprocess.run(["node", "--check", path], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
            return (r.returncode == 0), (r.stderr or "")
        except Exception as e:
            return False, str(e)
    return True, ""


def _find_unique(lines, pattern):
    return [i + 1 for i, ln in enumerate(lines) if pattern in ln]


def _extract_imports(lines):
    imports = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            imports.append(ln if ln.endswith("\n") else ln + "\n")
    return imports


def _find_used_imports(block_text, source_imports):
    used = []
    for imp in source_imports:
        s = imp.strip()
        if s.startswith("import "):
            body = s[len("import "):]
            names = [n.strip().split(" as ")[-1].strip() for n in body.split(",")]
        elif s.startswith("from "):
            parts = s.split(" import ")
            if len(parts) != 2:
                continue
            names = [n.strip().split(" as ")[-1].strip() for n in parts[1].split(",")]
        else:
            continue
        for n in names:
            if not n or n == "*":
                continue
            if n in block_text:
                used.append(imp)
                break
    return used



def _extract_imports(lines):
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            out.append(ln if ln.endswith("\n") else ln + "\n")
    return out


def _find_used_imports(block_text, source_imports):
    used = []
    for imp in source_imports:
        s = imp.strip()
        if s.startswith("import "):
            names = [n.strip().split(" as ")[-1].split(".")[0] for n in s[7:].split(",")]
        elif s.startswith("from "):
            parts = s.split(" import ")
            if len(parts) != 2:
                continue
            names = [n.strip().split(" as ")[-1] for n in parts[1].split(",")]
        else:
            continue
        for n in names:
            if n and n != "*" and n in block_text:
                used.append(imp)
                break
    return used



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
        if os.path.dirname(src) != os.path.dirname(newf):
            raise ValueError("source_file 和 new_file 必须在同一目录: %s vs %s" % (os.path.dirname(src), os.path.dirname(newf)))

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

        # v1.2: 从 end-1 往前找最后一个包含 } 的行，把尾部注释/空行保留在主文件里
        _actual_end = end - 1
        while _actual_end > start:
            _line = lines[_actual_end - 1].strip()
            if _line and ('}' in _line):
                break
            _actual_end -= 1
        if _actual_end <= start:
            raise ValueError("找不到函数结束的 }")
        end = _actual_end + 1   # 1-based，下一行

        block = lines[start - 1:end - 1]
        if not block:
            raise ValueError("切片为空")

        # 括号平衡检查
        _ob = sum(ln.count("{") for ln in block)
        _cb = sum(ln.count("}") for ln in block)
        if _ob != _cb:
            raise ValueError("切片括号不平衡: {=%d, }=%d" % (_ob, _cb))

        if any(end_pattern in ln for ln in block):
            raise ValueError("切片包含 end_pattern")
        if not any(start_pattern in ln for ln in block):
            raise ValueError("切片不包含 start_pattern")

        src_backup = _backup(src)

        os.makedirs(os.path.dirname(newf) or ".", exist_ok=True)
        source_imports = _extract_imports(lines)
        block_text = "".join(block)
        used_imports = _find_used_imports(block_text, source_imports)
        source_imports = _extract_imports(lines)
        block_text = "".join(block)
        used_imports = _find_used_imports(block_text, source_imports)
        with open(newf, "w", encoding="utf-8") as f:
            f.writelines(used_imports)
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
            if start <= a_hits[0] < end:
                raise ValueError("import_anchor 位于代码块内部（行%d），会导致删除范围错乱" % a_hits[0])
            base = os.path.basename(newf)
            imp_line = "import './" + base + "';\n"
            lines.insert(a_hits[0], imp_line)
            with open(src, "w", encoding="utf-8") as f:
                f.writelines(lines)
            ok, err = _syntax_ok(src)
            result["main_file_syntax_ok"] = ok
            if not ok:
                raise ValueError("源文件加 import 后语法错误: " + err)
            if start > a_hits[0]:
                start += 1
            if end > a_hits[0]:
                end += 1

        del lines[start - 1:end - 1]
        if replace_with:
            rep = replace_with
            if not rep.endswith("\n"):
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
