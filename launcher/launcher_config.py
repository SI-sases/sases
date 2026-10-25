# SASES Launcher Module
import json, os
import sys

DEFAULT_CONFIG = {
    "port": 8001,
    "python_path": "python",
    "script_path": "scripts/run_forever.py",
    "work_dir": "."
}

def _config_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "launcher_config.json")

def load_config():
    path = _config_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return dict(DEFAULT_CONFIG)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(data)
    return cfg

def ensure_default_config():
    path = _config_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

    cfg = load_config()
    if getattr(sys, 'frozen', False):
        # 打包后的 EXE 所在目录
        base = os.path.dirname(sys.executable)
        # 如果是本地在 dist 目录下测试，往上找一级根目录
        if os.path.basename(base) == 'dist':
            base = os.path.dirname(os.path.dirname(base))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    embed_py = os.path.join(base, "python-embed", "python.exe")
    venv_py = os.path.join(base, "venv312", "Scripts", "python.exe")

    if os.path.exists(embed_py):
        cfg["python_path"] = embed_py
    elif os.path.exists(venv_py):
        cfg["python_path"] = venv_py
    else:
        cfg["python_path"] = "python"

    return cfg

def resolve_path(p):
    if not p or p == "python":
        return p
    if os.path.isabs(p):
        return p

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    curr = base
    for _ in range(5):
        test_path = os.path.join(curr, p)
        if os.path.exists(test_path):
            return test_path
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent

    return os.path.join(base, p)
