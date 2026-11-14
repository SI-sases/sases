# core/services/harness_service.py
import os
import json
import importlib.util


def _get_modules_dir():
    """获取 harness_modules 目录绝对路径"""
    return os.path.join(os.path.dirname(__file__), '..', '..', 'harness_modules')


def list_modules():
    """扫描 harness_modules 目录，返回所有模块信息"""
    modules = []
    base_dir = _get_modules_dir()
    if not os.path.exists(base_dir):
        return modules

    for item in os.listdir(base_dir):
        module_dir = os.path.join(base_dir, item)
        if not os.path.isdir(module_dir):
            continue
        manifest_path = os.path.join(module_dir, 'manifest.json')
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                modules.append({
                    "id": manifest.get("id", item),
                    "name": manifest.get("name", item),
                    "description": manifest.get("description", "")
                })
            except Exception:
                # 忽略读取失败的模块
                pass
    return modules


def execute_module(module_id: str, params: dict):
    """动态加载并执行指定模块"""
    base_dir = _get_modules_dir()
    module_dir = os.path.join(base_dir, module_id)
    if not os.path.isdir(module_dir):
        raise ValueError(f"模块不存在: {module_id}")

    main_file = os.path.join(module_dir, 'main.py')
    if not os.path.isfile(main_file):
        raise ValueError(f"模块缺少 main.py: {module_id}")

    # 动态加载模块文件
    spec = importlib.util.spec_from_file_location(module_id, main_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 尝试调用模块的 run 函数，若不存在则报错
    if hasattr(mod, 'run'):
        return mod.run(params)
    elif hasattr(mod, 'execute'):
        return mod.execute(params)
    else:
        raise ValueError(f"模块未定义 run 或 execute 函数: {module_id}")
