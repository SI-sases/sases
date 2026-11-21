# core/tool_sandbox_runner.py
# -*- coding: utf-8 -*-
"""在隔离子进程里加载外部工具并执行 run(params)。

约束：
- 只读：模块目录（含其数据文件）
- 可写：临时 scratch 目录（进程结束即删）
- 禁网：socket / ssl / http / requests / httpx / aiohttp
- 禁子进程：subprocess / ctypes / multiprocessing
"""
import builtins
import importlib.util
import json
import os
import sys

MARKER = "__SASES_RESULT__"


class _Blocker:
    _BLOCKED = {
        "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib",
        "xmlrpc", "requests", "httpx", "aiohttp", "websocket", "websockets",
        "subprocess", "ctypes", "multiprocessing", "pty", "winreg",
    }

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self._BLOCKED:
            raise ImportError("sandbox: module '" + fullname + "' is blocked")
        return None


def _install_blocker():
    for name in list(sys.modules):
        if name.split(".")[0] in _Blocker._BLOCKED:
            del sys.modules[name]
    sys.meta_path.insert(0, _Blocker())


def _install_fs_guard(module_dir, scratch):
    real_open = builtins.open
    read_roots = [os.path.abspath(module_dir)]
    write_root = os.path.abspath(scratch)

    def _inside(path, root):
        return path == root or path.startswith(root + os.sep)

    def guarded_open(file, mode="r", *args, **kwargs):
        if isinstance(file, int):
            return real_open(file, mode, *args, **kwargs)
        try:
            p = os.path.abspath(os.fspath(file))
        except Exception:
            return real_open(file, mode, *args, **kwargs)
        m = mode or "r"
        writing = any(c in m for c in "wax+")
        if writing:
            if not _inside(p, write_root):
                raise PermissionError("sandbox: write denied outside scratch: " + p)
        else:
            if not any(_inside(p, r) for r in read_roots):
                raise PermissionError("sandbox: read denied outside module dir: " + p)
        return real_open(file, m, *args, **kwargs)

    builtins.open = guarded_open

    real_os_open = os.open

    def guarded_os_open(path, flags, *args, **kwargs):
        try:
            p = os.path.abspath(os.fspath(path))
        except Exception:
            return real_os_open(path, flags, *args, **kwargs)
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC))
        if writing:
            if not _inside(p, write_root):
                raise PermissionError("sandbox: os.open write denied: " + p)
        else:
            if not any(_inside(p, r) for r in read_roots):
                raise PermissionError("sandbox: os.open read denied: " + p)
        return real_os_open(path, flags, *args, **kwargs)

    os.open = guarded_os_open


def main():
    payload = json.loads(sys.stdin.read() or "{}")
    module_dir = payload.get("module_dir") or ""
    entrypoint = payload.get("entrypoint") or "main.py"
    params = payload.get("params") or {}
    scratch = payload.get("scratch") or ""

    # 工具自身的 print 全部转到 stderr，stdout 只留给结果标记
    _real_stdout = sys.stdout
    sys.stdout = sys.stderr

    def _finish(ok, result=None, error=None):
        sys.stdout = _real_stdout
        if ok:
            try:
                text = json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                ok, error = False, "result not JSON serializable: " + str(e)
                text = ""
        else:
            text = ""
        out = {"ok": bool(ok), "result": result if ok else None, "error": None if ok else str(error)}
        try:
            line = json.dumps(out, ensure_ascii=False, default=str)
        except Exception:
            line = json.dumps({"ok": False, "error": "result not serializable"})
        print(MARKER + line)
        sys.stdout.flush()

    try:
        if not os.path.isdir(module_dir):
            _finish(False, error="module dir not found")
            return
        sys.path.insert(0, module_dir)
        _install_blocker()
        _install_fs_guard(module_dir, scratch)

        spec = importlib.util.spec_from_file_location(
            "sases_external_tool", os.path.join(module_dir, entrypoint))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        run = getattr(mod, "run", None)
        if not callable(run):
            _finish(False, error="entrypoint must define run(params)")
            return
        result = run(params)
        _finish(True, result=result)
    except BaseException as e:
        try:
            _finish(False, error=type(e).__name__ + ": " + str(e))
        except Exception:
            pass


if __name__ == "__main__":
    main()
