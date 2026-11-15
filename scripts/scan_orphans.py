"""
SASES 幽灵依赖扫描器 v4
修复 v3 的 bug：collect_py_definitions 支持 import * 递归继承
保留 v3 的：re-export 识别、TYPE_CHECKING 跳过、try/except 跳过、子模块检查
"""

import ast, os, re, json, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
STATIC = ROOT / "static"
HARNESS = ROOT / "harness_modules"

IGNORE_DIRS = {
    "__pycache__", ".backups", "venv312", "venv", "site-packages",
    "tests", "node_modules", ".git", "build", "dist",
}

IGNORE_PROTOCOLS = {"CONTENT"}


def walk_files(base, ext):
    if not base.exists():
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith(ext):
                yield Path(root) / f


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _resolve_module_path(py, node):
    """给 collect_py_definitions 用：把 import 节点解析成 .py 路径"""
    if node.level and node.level > 0:
        pkg_dir = py.resolve().parent
        for _ in range(node.level - 1):
            pkg_dir = pkg_dir.parent
        if not node.module:
            return None
        target = pkg_dir
        for p in node.module.split("."):
            target = target / p
        if target.with_suffix(".py").exists():
            return target.with_suffix(".py")
        if (target / "__init__.py").exists():
            return target / "__init__.py"
        return None
    else:
        mod = node.module or ""
        if not (mod.startswith("core") or mod.startswith("harness_modules")):
            return None
        target = ROOT
        for p in mod.split("."):
            target = target / p
        if target.with_suffix(".py").exists():
            return target.with_suffix(".py")
        if (target / "__init__.py").exists():
            return target / "__init__.py"
        return None


def collect_py_definitions():
    """收集所有定义，支持 from X import * 的递归继承，支持 AnnAssign"""
    raw_defs = defaultdict(dict)
    star_imports = defaultdict(set)

    for py in list(walk_files(CORE, ".py")) + list(walk_files(HARNESS, ".py")):
        try:
            tree = ast.parse(read_text(py))
        except SyntaxError as e:
            print(f"[警告] {py} 语法错误，跳过: {e}")
            continue
        names = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names[node.name] = node.lineno
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names[t.id] = node.lineno
            elif isinstance(node, ast.AnnAssign):
                # ★ 新增：带类型注解的赋值  _pending: dict = {}
                if isinstance(node.target, ast.Name):
                    names[node.target.id] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                has_star = any(a.name == "*" for a in node.names)
                if has_star:
                    target = _resolve_module_path(py, node)
                    if target:
                        star_imports[str(py)].add(str(target))
                    continue
                for alias in node.names:
                    if alias.name != "*":
                        names[alias.name] = node.lineno
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        names[alias.asname] = node.lineno
                    else:
                        names[alias.name.split(".")[0]] = node.lineno
        raw_defs[str(py)] = names

    # 递归合并 import *
    defs = dict(raw_defs)
    for _ in range(3):
        changed = False
        for py, targets in star_imports.items():
            for target in targets:
                if target not in raw_defs:
                    continue
                for name, line in raw_defs[target].items():
                    if name not in defs[py]:
                        defs[py][name] = line
                        changed = True
        if not changed:
            break

    return defs


def resolve_import(py, node):
    """返回 (target_file, target_dir) 或 "SKIP" """
    if node.level and node.level > 0:
        pkg_dir = py.resolve().parent
        for _ in range(node.level - 1):
            pkg_dir = pkg_dir.parent
        if node.module:
            target = pkg_dir
            for p in node.module.split("."):
                target = target / p
            if target.with_suffix(".py").exists():
                return target.with_suffix(".py"), target.parent
            if (target / "__init__.py").exists():
                return target / "__init__.py", target
            return None, None
        else:
            init = pkg_dir / "__init__.py"
            if init.exists():
                return init, pkg_dir
            return None, None
    else:
        mod = node.module or ""
        if not mod:
            return "SKIP"
        if not (mod.startswith("core") or mod.startswith("harness_modules")):
            return "SKIP"
        target = ROOT
        for p in mod.split("."):
            target = target / p
        if target.with_suffix(".py").exists():
            return target.with_suffix(".py"), target.parent
        if (target / "__init__.py").exists():
            return target / "__init__.py", target
        return None, None


def scan_dangling_imports(defs):
    issues = []
    for py in walk_files(CORE, ".py"):
        try:
            tree = ast.parse(read_text(py))
        except SyntaxError:
            continue

        type_checking_lines = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) \
                    and node.test.id == "TYPE_CHECKING":
                for sub in ast.walk(node):
                    if hasattr(sub, "lineno"):
                        type_checking_lines.add(sub.lineno)

        try_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for h in node.handlers:
                    if h.type and isinstance(h.type, ast.Name) and h.type.id == "ImportError":
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.ImportFrom):
                                try_imports.add((sub.lineno, sub.module))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "*":
                continue
            if node.lineno in type_checking_lines:
                continue
            if (node.lineno, node.module) in try_imports:
                continue

            result = resolve_import(py, node)
            if result == "SKIP":
                continue
            target_file, target_dir = result

            if not target_file:
                issues.append({
                    "level": "P0", "type": "module_not_found",
                    "file": str(py.relative_to(ROOT)), "line": node.lineno,
                    "module": node.module, "level_num": node.level,
                })
                continue

            target_defs = defs.get(str(target_file), {})

            for alias in node.names:
                if alias.name == "*":
                    continue
                if alias.name in target_defs:
                    continue
                if target_dir:
                    if (target_dir / f"{alias.name}.py").exists():
                        continue
                    if (target_dir / alias.name / "__init__.py").exists():
                        continue
                issues.append({
                    "level": "P0", "type": "name_not_found",
                    "file": str(py.relative_to(ROOT)), "line": node.lineno,
                    "module": node.module, "name": alias.name,
                    "target_file": str(target_file.relative_to(ROOT)),
                    "target_has": list(target_defs.keys())[:15],
                })
    return issues


def scan_router_ghosts():
    bootstrap = CORE / "bootstrap.py"
    if not bootstrap.exists():
        return []
    content = read_text(bootstrap)
    issues = []
    import_map = {}
    for m in re.finditer(r"from\s+(core\.api_routes(?:\.[\w\.]+)?)\s+import\s+([^\n]+)", content):
        mod_path = m.group(1).replace(".", "/")
        module_file = ROOT / f"{mod_path}.py"
        if not module_file.exists():
            module_file = ROOT / mod_path / "__init__.py"
        for name in m.group(2).split(","):
            name = name.strip().split(" as ")[-1].strip()
            if name and name != "*" and "(" not in name:
                import_map[name] = module_file

    for m in re.finditer(r"include_router\(\s*([\w\.]+)", content):
        expr = m.group(1)
        var = expr.split(".")[0]
        line = content[: m.start()].count("\n") + 1
        if var not in import_map:
            continue
        module_file = import_map[var]
        if not module_file.exists():
            issues.append({"level": "P0", "type": "router_file_missing",
                           "line": line, "var": var})
            continue
        if "." in expr:
            target_var = expr.split(".", 1)[1].split(".")[0]
            if not re.search(rf"^\s*{re.escape(target_var)}\s*=",
                             read_text(module_file), re.M):
                issues.append({"level": "P0", "type": "router_var_missing",
                               "line": line, "var": target_var,
                               "module_file": str(module_file.relative_to(ROOT))})
    return issues


def scan_window_ghosts():
    mounted = set()
    for js in walk_files(STATIC / "modules", ".js"):
        content = read_text(js)
        mounted.update(re.findall(r"window\.(\w+)\s*=", content))
        mounted.update(re.findall(r'window\[["\'](\w+)["\']\]\s*=', content))

    issues = []
    all_files = list(walk_files(STATIC, ".html")) + list(walk_files(STATIC / "modules", ".js"))
    for f in all_files:
        content = read_text(f)
        for m in re.finditer(r'onclick\s*=\s*["\'](?:window\.)?(\w+)\s*\(', content):
            name = m.group(1)
            if name in {"event", "this", "window", "document", "location",
                        "alert", "confirm", "prompt", "fetch"}:
                continue
            if name not in mounted:
                line = content[: m.start()].count("\n") + 1
                issues.append({"level": "P1", "type": "window_not_mounted",
                               "file": str(f.relative_to(ROOT)), "line": line,
                               "name": name})
    return issues


def scan_protocol_prefixes():
    backend = set()
    for py in walk_files(CORE, ".py"):
        content = read_text(py)
        backend.update(re.findall(r'["\']\[([A-Z_0-9]+)\]:', content))
        backend.update(re.findall(r'f["\']\[([A-Z_0-9]+)\]:', content))

    frontend = set()
    for js in walk_files(STATIC / "modules", ".js"):
        content = read_text(js)
        frontend.update(re.findall(r'["\']\[([A-Z_0-9]+)\]:', content))
        frontend.update(re.findall(r'`\[([A-Z_0-9]+)\]:', content))

    return {
        "backend_prefixes": sorted(backend),
        "frontend_prefixes": sorted(frontend),
        "sent_not_rendered": sorted(backend - frontend - IGNORE_PROTOCOLS),
        "rendered_not_sent": sorted(frontend - backend),
    }


def main():
    print("=" * 60)
    print("SASES 幽灵依赖扫描器 v4")
    print("=" * 60)

    print("\n[1/5] 收集定义（含 import * 递归）...")
    defs = collect_py_definitions()
    print(f"   已扫描 {len(defs)} 个 Python 文件")

    print("\n[2/5] 扫描悬空导入...")
    dangling = scan_dangling_imports(defs)
    print(f"   发现 {len(dangling)} 条 P0")

    print("\n[3/5] 扫描路由幽灵...")
    router_ghosts = scan_router_ghosts()
    print(f"   发现 {len(router_ghosts)} 条 P0")

    print("\n[4/5] 扫描前端 window 幽灵...")
    window_ghosts = scan_window_ghosts()
    print(f"   发现 {len(window_ghosts)} 条 P1")

    print("\n[5/5] 扫描协议前缀...")
    protocol = scan_protocol_prefixes()
    print(f"   后端发 {len(protocol['sent_not_rendered'])} 条前端未渲染")

    report = {
        "dangling_imports": dangling,
        "router_ghosts": router_ghosts,
        "window_ghosts": window_ghosts,
        "protocol_prefixes": protocol,
        "summary": {
            "p0_total": len(dangling) + len(router_ghosts),
            "p1_total": len(window_ghosts) + len(protocol["sent_not_rendered"]),
        },
    }

    out = ROOT / "scripts" / "orphans_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n完整报告：{out}")

    print("\n" + "=" * 60)
    print(f"P0（必须清零）：{report['summary']['p0_total']} 条")
    print(f"P1（必须清零）：{report['summary']['p1_total']} 条")
    print("=" * 60)

    if dangling:
        print("\n--- P0 悬空导入 ---")
        for d in dangling[:40]:
            n = d.get("name", "*")
            t = d.get("target_file", "")
            print(f"  {d['file']}:{d['line']}  {d['module']}.{n}"
                  + (f"  → {t}" if t else ""))

    if router_ghosts:
        print("\n--- P0 路由幽灵 ---")
        for r in router_ghosts:
            print(f"  L{r.get('line', '?')}  {r['type']}  {r.get('var', '')}")

    if window_ghosts:
        print("\n--- P1 window 未挂载 ---")
        for w in window_ghosts[:20]:
            print(f"  {w['file']}:{w['line']}  {w['name']}")

    if protocol["sent_not_rendered"]:
        print("\n--- P1 后端发但前端不渲染 ---")
        for p in protocol["sent_not_rendered"]:
            print(f"  [{p}]:")

    return 0 if report["summary"]["p0_total"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
