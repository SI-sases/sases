# core/tool_install_service.py
# -*- coding: utf-8 -*-
"""外部工具安装：ZIP 上传 / git 白名单拉取。

原则：
- 安装期不执行任何工具代码
- 只接受 manifest.json + entrypoint 的纯文件包
- 校验 id / 保留名 / 路径穿越 / 大小 / sha256
- 安装后默认 disabled，由用户显式启用
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from typing import Any, Dict, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(ROOT, "harness_modules")
EXTERNAL_DIR = os.path.join(MODULES_DIR, "_external")
BACKUP_DIR = os.path.join(ROOT, ".backups", "tools")
SOURCES_CFG = os.path.join(ROOT, "data", "tool_sources.json")

ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
MAX_ZIP_BYTES = 5 * 1024 * 1024
MAX_EXTRACT_BYTES = 20 * 1024 * 1024
MAX_FILES = 200
GIT_TIMEOUT = 60


class InstallError(Exception):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _builtin_ids() -> set:
    out = set()
    if not os.path.isdir(MODULES_DIR):
        return out
    for name in os.listdir(MODULES_DIR):
        p = os.path.join(MODULES_DIR, name)
        if name.startswith("_") or not os.path.isdir(p):
            continue
        if os.path.exists(os.path.join(p, "manifest.json")):
            out.add(name)
    return out


def allowed_git_sources() -> list:
    """git 安装白名单：data/tool_sources.json 或 SASES_TOOL_GIT_ALLOWLIST（逗号分隔）。"""
    items = []
    try:
        if os.path.exists(SOURCES_CFG):
            with open(SOURCES_CFG, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                items = data.get("git_allowlist") or []
    except Exception:
        items = []
    env = os.getenv("SASES_TOOL_GIT_ALLOWLIST", "")
    if env:
        items.extend([x.strip() for x in env.split(",") if x.strip()])
    return [str(x) for x in items]


def _git_allowed(repo: str) -> bool:
    repo = (repo or "").strip().lower()
    if not repo:
        return False
    for prefix in allowed_git_sources():
        if repo.startswith(str(prefix).strip().lower()):
            return True
    return False


def _safe_members(zf: zipfile.ZipFile) -> list:
    out = []
    total = 0
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
            raise InstallError("ZIP 包含绝对路径: " + name)
        parts = [p for p in name.split("/") if p not in ("", ".")]
        if any(p == ".." for p in parts):
            raise InstallError("ZIP 包含路径穿越: " + name)
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise InstallError("ZIP 包含符号链接: " + name)
        total += info.file_size
        if total > MAX_EXTRACT_BYTES:
            raise InstallError("ZIP 解压后过大（>" + str(MAX_EXTRACT_BYTES) + " bytes）")
        out.append(info)
    if len(out) > MAX_FILES:
        raise InstallError("ZIP 文件数过多（>" + str(MAX_FILES) + "）")
    return out


def _find_package_root(extract_dir: str) -> str:
    if os.path.exists(os.path.join(extract_dir, "manifest.json")):
        return extract_dir
    entries = [e for e in os.listdir(extract_dir) if not e.startswith("__MACOSX")]
    dirs = [e for e in entries if os.path.isdir(os.path.join(extract_dir, e))]
    if len(dirs) == 1 and os.path.exists(os.path.join(extract_dir, dirs[0], "manifest.json")):
        return os.path.join(extract_dir, dirs[0])
    raise InstallError("包内找不到 manifest.json（支持根目录或单层子目录）")


def _validate_package(pkg_dir: str) -> Dict[str, Any]:
    mpath = os.path.join(pkg_dir, "manifest.json")
    try:
        with open(mpath, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        raise InstallError("manifest.json 解析失败: " + str(e))
    if not isinstance(manifest, dict):
        raise InstallError("manifest.json 必须是对象")

    mid = str(manifest.get("id") or "").strip()
    if not ID_RE.match(mid):
        raise InstallError("非法 id（要求小写字母开头，3-41 位小写字母/数字/下划线）: " + mid)
    if mid in _builtin_ids():
        raise InstallError("id 与内置工具冲突: " + mid)
    if mid.startswith("ext_api_"):
        raise InstallError("id 不能以 ext_api_ 开头")

    entry = str(manifest.get("entrypoint") or "main.py").strip()
    if not entry.endswith(".py") or "/" in entry or "\\" in entry or ".." in entry:
        raise InstallError("entrypoint 必须是包内单个 .py 文件: " + entry)
    if not os.path.isfile(os.path.join(pkg_dir, entry)):
        raise InstallError("entrypoint 不存在: " + entry)

    if not str(manifest.get("name") or "").strip():
        raise InstallError("manifest 缺少 name")

    return {"manifest": manifest, "id": mid, "entrypoint": entry}


def _install_dir(pkg_dir: str, meta: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    from core import tool_registry

    v = _validate_package(pkg_dir)
    mid = v["id"]
    target = os.path.join(EXTERNAL_DIR, mid)
    if os.path.exists(target):
        if not force:
            raise InstallError("工具已存在: " + mid + "（如需覆盖请传 force=true）")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        bak = os.path.join(BACKUP_DIR, mid + "_" + time.strftime("%Y%m%d_%H%M%S"))
        shutil.move(target, bak)
        print("[tools] 旧版本已备份: " + bak)

    os.makedirs(EXTERNAL_DIR, exist_ok=True)
    try:
        shutil.copytree(pkg_dir, target)
    except Exception as e:
        raise InstallError("写入工具目录失败: " + str(e))

    sha = _sha256_file(os.path.join(target, v["entrypoint"]))
    source = dict(meta.get("source") or {})
    source["sha256"] = sha
    ok = tool_registry.register(
        mid,
        source=source,
        enabled=False,
        version=str(v["manifest"].get("version") or ""),
        extra={"name": v["manifest"].get("name"), "installed_by": meta.get("installed_by")},
    )
    if not ok:
        shutil.rmtree(target, ignore_errors=True)
        raise InstallError("写入注册表失败")

    try:
        from core.harness_runtime import harness_runtime
        harness_runtime.reload_modules()
    except Exception as e:
        print("[tools] reload_modules 失败: " + str(e))

    return {"id": mid, "version": str(v["manifest"].get("version") or ""),
            "sha256": sha, "enabled": False, "path": os.path.relpath(target, ROOT)}


def install_from_zip(zip_bytes: bytes, filename: str = "", force: bool = False,
                     installed_by: Optional[int] = None) -> Dict[str, Any]:
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise InstallError("ZIP 过大（>" + str(MAX_ZIP_BYTES) + " bytes）")
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as e:
        raise InstallError("不是有效的 ZIP: " + str(e))

    with tempfile.TemporaryDirectory(prefix="sases_install_") as td:
        for info in _safe_members(zf):
            zf.extract(info, td)
        zf.close()
        pkg = _find_package_root(td)
        return _install_dir(pkg, {
            "source": {"type": "zip", "filename": filename, "zip_sha256": _sha256_bytes(zip_bytes)},
            "installed_by": installed_by,
        }, force=force)


def install_from_git(repo: str, ref: str = "", subpath: str = "", force: bool = False,
                     installed_by: Optional[int] = None) -> Dict[str, Any]:
    repo = (repo or "").strip()
    if not _git_allowed(repo):
        raise InstallError("仓库不在白名单内（配置 data/tool_sources.json 或 SASES_TOOL_GIT_ALLOWLIST）: " + repo)
    subpath = (subpath or "").strip().strip("/")
    if ".." in subpath.split("/"):
        raise InstallError("subpath 非法")

    with tempfile.TemporaryDirectory(prefix="sases_git_") as td:
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "never"
        cmd = ["git", "clone", "--depth", "1"]
        if ref:
            cmd += ["--branch", ref]
        cmd += [repo, td + "/src"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=GIT_TIMEOUT,
                               env=env, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            raise InstallError("git clone 超时（>" + str(GIT_TIMEOUT) + "s）")
        if r.returncode != 0:
            raise InstallError("git clone 失败: " + (r.stderr or r.stdout or "")[-300:])

        src_root = td + "/src"
        commit = ""
        try:
            rc = subprocess.run(["git", "-C", src_root, "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=10, env=env)
            commit = (rc.stdout or "").strip()
        except Exception:
            pass

        pkg = os.path.join(src_root, subpath) if subpath else _find_package_root(src_root)
        if not os.path.isdir(pkg):
            raise InstallError("subpath 不存在: " + subpath)
        return _install_dir(pkg, {
            "source": {"type": "git", "repo": repo, "ref": ref, "commit": commit, "subpath": subpath},
            "installed_by": installed_by,
        }, force=force)


def set_enabled(module_id: str, enabled: bool) -> Dict[str, Any]:
    from core import tool_registry
    if not tool_registry.get(module_id):
        raise InstallError("未安装该外部工具: " + module_id)
    if not tool_registry.set_enabled(module_id, enabled):
        raise InstallError("更新启用状态失败")
    try:
        from core.harness_runtime import harness_runtime
        harness_runtime.reload_modules()
    except Exception as e:
        print("[tools] reload_modules 失败: " + str(e))
    return {"id": module_id, "enabled": bool(enabled)}


def uninstall(module_id: str) -> Dict[str, Any]:
    from core import tool_registry
    entry = tool_registry.get(module_id)
    if not entry or not entry.get("external"):
        raise InstallError("只能卸载外部工具: " + module_id)
    target = os.path.join(EXTERNAL_DIR, module_id)
    if os.path.isdir(target):
        shutil.rmtree(target, ignore_errors=True)
    tool_registry.remove(module_id)
    try:
        from core.harness_runtime import harness_runtime
        harness_runtime.reload_modules()
    except Exception as e:
        print("[tools] reload_modules 失败: " + str(e))
    return {"id": module_id, "removed": True}


def catalog() -> Dict[str, Any]:
    from core import tool_registry
    items = []
    seen = set()
    try:
        from core.harness_runtime import harness_runtime
        for t in harness_runtime.list_tools():
            if t.module_id in seen:
                continue
            seen.add(t.module_id)
            items.append({"id": t.module_id, "name": t.name, "version": t.version,
                          "description": t.description, "external": False, "enabled": True})
    except Exception as e:
        print("[tools] catalog builtin 读取失败: " + str(e))

    for mid, entry in tool_registry.list_tools().items():
        if mid in seen:
            continue
        seen.add(mid)
        name, version = mid, entry.get("version", "")
        mpath = os.path.join(EXTERNAL_DIR, mid, "manifest.json")
        try:
            with open(mpath, "r", encoding="utf-8") as f:
                m = json.load(f)
            name = m.get("name") or name
            version = m.get("version") or version
        except Exception:
            pass
        items.append({
            "id": mid,
            "name": name,
            "version": version,
            "external": True,
            "enabled": bool(entry.get("enabled")),
            "source": entry.get("source") or {},
            "installed_at": entry.get("installed_at"),
        })
    return {"count": len(items), "tools": items,
            "git_allowlist": allowed_git_sources()}
