# SASES Launcher Module
import json, os

DEFAULT_CONFIG = {
    "port": 8001,
    "python_path": "venv312/Scripts/python.exe",
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
    import os
    import json
    path = _config_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    return load_config()


def resolve_path(p):
    if os.path.isabs(p):
        return p
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, p)
