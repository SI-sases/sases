import json
import os

import tkinter as tk
from tkinter import ttk

try:
    from launcher.launcher_config import DEFAULT_CONFIG
except Exception:
    try:
        from launcher_config import DEFAULT_CONFIG
    except Exception:
        DEFAULT_CONFIG = {}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "launcher_config.json")


def load_config(path=None):
    target = path or CONFIG_PATH
    data = dict(DEFAULT_CONFIG)
    try:
        with open(target, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except Exception:
        pass
    return data


def save_config(data, path=None):
    target = path or CONFIG_PATH
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return target


class ConfigPage(ttk.Frame):
    def __init__(self, master, config_path=None, **kwargs):
        super().__init__(master, **kwargs)
        self.config_path = config_path
        self.vars = {}
        self._build()
        self.load()

    def _build(self):
        ttk.Label(self, text="配置", font=("Microsoft YaHei", 14, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        form = ttk.Frame(self)
        form.pack(fill="both", expand=True, padx=12, pady=6)
        for i, (key, value) in enumerate(DEFAULT_CONFIG.items()):
            ttk.Label(form, text=str(key)).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            var = tk.StringVar(value=str(value))
            self.vars[key] = var
            ttk.Entry(form, textvariable=var, width=40).grid(row=i, column=1, sticky="ew", padx=6, pady=4)
        ttk.Button(self, text="保存", command=self.save).pack(anchor="e", padx=12, pady=10)

    def load(self):
        cfg = load_config(self.config_path)
        for key, var in self.vars.items():
            if key in cfg:
                var.set(str(cfg[key]))

    def save(self):
        data = {}
        for key, var in self.vars.items():
            raw = var.get()
            default = DEFAULT_CONFIG.get(key)
            if isinstance(default, bool):
                data[key] = raw.strip().lower() in ("1", "true", "yes", "on")
            elif isinstance(default, int):
                try:
                    data[key] = int(raw)
                except ValueError:
                    data[key] = default
            else:
                data[key] = raw
        save_config(data, self.config_path)
        return data
