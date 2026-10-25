import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. 修复 launcher_config.py 的 resolve_path 逻辑
cfg_path = os.path.join(ROOT, "launcher", "launcher_config.py")
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg_code = f.read()

old_resolve = """def resolve_path(p):
    if os.path.isabs(p):
        return p
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, p)"""

new_resolve = """def resolve_path(p):
    if not p or p == "python":
        return p
    if os.path.isabs(p):
        return p
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, p)"""

if old_resolve in cfg_code:
    cfg_code = cfg_code.replace(old_resolve, new_resolve)
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(cfg_code)
    print("Fixed: launcher_config.py resolve_path")

# 2. 修复 main_window.py 的路径解析和托盘图标
mw_path = os.path.join(ROOT, "launcher", "ui", "main_window.py")
with open(mw_path, "r", encoding="utf-8") as f:
    mw_code = f.read()

# 修复初始化时的路径
old_init = """        self.work_dir = self.cfg.get("work_dir", "")"""
new_init = """        self.work_dir = launcher_config.resolve_path(self.cfg.get("work_dir", ""))
        self.script_path = launcher_config.resolve_path(self.cfg.get("script_path", ""))
        self.python_path = launcher_config.resolve_path(self.cfg.get("python_path", ""))"""
if old_init in mw_code:
    mw_code = mw_code.replace(old_init, new_init)

# 修复托盘图标
old_tray = """        _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icon.ico')"""
new_tray = """        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _ico = os.path.join(base_dir, 'launcher', 'icon.ico')
        if not os.path.exists(_ico):
            _ico = os.path.join(base_dir, 'icon.ico')"""
if old_tray in mw_code:
    mw_code = mw_code.replace(old_tray, new_tray)

with open(mw_path, "w", encoding="utf-8") as f:
    f.write(mw_code)
    print("Fixed: main_window.py paths and tray icon")