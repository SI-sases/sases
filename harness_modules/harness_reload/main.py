"""重新加载所有 harness 模块。用于三者写完新工具后立即生效。

注意：不能顶层 import harness_runtime，否则会循环导入。
"""


def run(params):
    try:
        from core.harness_runtime import harness_runtime
    except Exception as e:
        return {'success': False, 'error': 'import harness_runtime 失败: ' + str(e)}

    reload_fn = None
    for name in ('reload_modules', 'reload', 'try_reload_harness'):
        if hasattr(harness_runtime, name):
            reload_fn = getattr(harness_runtime, name)
            break

    if reload_fn is None:
        return {
            'success': False,
            'error': 'harness_runtime 没有 reload_modules / reload / try_reload_harness 方法',
            'available_methods': [m for m in dir(harness_runtime) if not m.startswith('_')]
        }

    try:
        result = reload_fn()
        return {
            'success': True,
            'message': 'harness 模块已重新加载',
            'method': reload_fn.__name__,
            'result': str(result)[:500] if result else 'ok'
        }
    except Exception as e:
        return {'success': False, 'error': 'reload 执行失败: ' + str(e)}