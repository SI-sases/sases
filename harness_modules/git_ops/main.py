# harness_modules/git_ops/main.py
"""Git 版本控制工具

安全设计：只暴露白名单动作，不开放任意 git 命令。
"""
import subprocess
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT, encoding="utf-8", errors="replace")
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"命令超时（{timeout}s）"
    except Exception as e:
        return -1, "", str(e)


def _safe_path(p):
    if not p:
        return False
    if p.startswith("/") or (len(p) > 1 and p[1] == ":"):
        return False
    if ".." in p.split("/") or ".." in p.split("\\"):
        return False
    return True


def run(params):
    action = (params.get("action") or "").lower()
    if not action:
        return {"success": False, "error": "缺少 action 参数"}

    if action == "status":
        code, out, err = _run("git status --short")
        return {"success": code == 0, "output": out[:3000], "error": err}

    if action == "diff":
        code, out, err = _run("git diff")
        return {"success": code == 0, "output": out[:3000], "error": err}

    if action == "log":
        n = int(params.get("n", 10))
        if n < 1 or n > 50:
            return {"success": False, "error": "n 必须在 1-50 之间"}
        code, out, err = _run(f"git log --oneline -{n}")
        return {"success": code == 0, "output": out, "error": err}

    if action == "add":
        target = params.get("file", ".")
        if target != "." and not _safe_path(target):
            return {"success": False, "error": f"非法路径: {target}"}
        code, out, err = _run(f"git add {target}")
        return {"success": code == 0, "output": out, "error": err}

    if action == "commit":
        _chk_code, _chk_out, _ = _run("git status --porcelain")
        if not _chk_out.strip():
            return {"success": True, "output": "nothing to commit, working tree clean", "error": ""}
        msg = params.get("message", "")
        if not msg:
            return {"success": False, "error": "缺少 commit message"}
        safe_msg = msg.replace('"', "'")
        code, out, err = _run(f'git commit -m "{safe_msg}"')
        return {"success": code == 0, "output": out[:2000], "error": err[:1000]}

    if action == "snapshot":
        msg = params.get("message", "")
        if not msg:
            return {"success": False, "error": "缺少 snapshot message"}
        safe_msg = msg.replace('"', "'")
        _run("git add -A")
        code, out, err = _run(f'git commit -m "{safe_msg}"')
        if code != 0:
            return {"success": False, "output": out[:2000], "error": err[:1000]}
        return {"success": True, "output": out[:2000], "message": safe_msg}

    if action == "push":
        branch = params.get("branch", "main")
        remote = params.get("remote", "origin")
        code, out, err = _run(f"git push {remote} {branch}", timeout=120)
        return {"success": code == 0, "output": out[:2000], "error": err[:1000]}

    if action == "pull":
        branch = params.get("branch", "main")
        remote = params.get("remote", "origin")
        code, out, err = _run(f"git pull {remote} {branch}", timeout=120)
        return {"success": code == 0, "output": out[:2000], "error": err[:1000]}

    if action == "rollback":
        n = int(params.get("steps", 1))
        if n < 1 or n > 20:
            return {"success": False, "error": "回滚步数必须在 1-20 之间"}
        code, out, err = _run(f"git reset --hard HEAD~{n}")
        if code != 0:
            return {"success": False, "error": err}
        code2, out2, _ = _run("git log --oneline -3")
        return {"success": True, "output": out[:500], "recent": out2, "warning": f"已回滚 {n} 步，此操作不可撤销"}

    if action == "remote_add":
        name = params.get("name", "origin")
        url = params.get("url", "")
        if not url:
            return {"success": False, "error": "缺少 url"}
        _run(f"git remote remove {name}")
        code, out, err = _run(f"git remote add {name} {url}")
        return {"success": code == 0, "output": out, "error": err}

    if action == "remote_list":
        code, out, err = _run("git remote -v")
        return {"success": code == 0, "output": out, "error": err}

    return {"success": False, "error": f"未知 action: {action}。支持: status/diff/log/add/commit/snapshot/push/pull/rollback/remote_add/remote_list"}