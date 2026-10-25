import json
import os
import importlib.util
import sys
from typing import Dict, Any, Optional

from core.harness_models import ModuleManifest, ToolDefinition, ToolInvokeResponse

HARNESS_MODULES_DIR = "harness_modules"

def _load_manifest(module_dir: str) -> Optional[ModuleManifest]:
    manifest_path = os.path.join(module_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ModuleManifest(**data)

def _load_module_function(module_dir: str, entrypoint: str, module_name: str):
    entry_path = os.path.join(module_dir, entrypoint)
    if not os.path.exists(entry_path):
        raise FileNotFoundError(f"Entrypoint {entry_path} not found")

    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, entry_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise AttributeError("Module entrypoint must define a run(params) function")
    return module.run

def load_harness_modules(modules_dir: str = HARNESS_MODULES_DIR) -> Dict[str, dict]:
    """扫描模块目录并返回 {module_id: {manifest, dir, run_fn}}"""
    modules = {}
    if not os.path.exists(modules_dir):
        return modules

    for module_id in os.listdir(modules_dir):
        module_dir = os.path.join(modules_dir, module_id)
        if not os.path.isdir(module_dir):
            continue
        manifest = _load_manifest(module_dir)
        if manifest is None:
            continue
        unique_module_name = f"harness_{manifest.id}"
        try:
            run_fn = _load_module_function(module_dir, manifest.entrypoint, unique_module_name)
        except Exception as e:
            print(f"Failed to load module {module_id}: {e}")
            continue
        entry = {
            "manifest": manifest,
            "dir": module_dir,
            "run_fn": run_fn
        }
        modules[manifest.id] = entry
        # v0.19: 注册别名
        _aliases = getattr(manifest, 'aliases', None) or []
        for _alias in _aliases:
            if isinstance(_alias, str) and _alias and _alias not in modules:
                modules[_alias] = entry
    return modules
