# core/services/agi_service.py
import importlib.util
import os


def _load_agi_coordinator():
    """动态加载 agi_coordinator 模块，返回模块对象"""
    path = os.path.join(os.path.dirname(__file__), '..', 'agi_coordinator.py')
    spec = importlib.util.spec_from_file_location("agi_coordinator", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def execute_agi_task(task_type: str, content: str, media_data: str = None):
    """执行 AGI 任务，根据类型分发"""
    coord = _load_agi_coordinator()

    if task_type == "text":
        # 文本任务直接返回内容（实际可调用聊天服务）
        return {"response": content}

    elif task_type == "image":
        if not media_data:
            raise ValueError("缺少图片数据")
        if hasattr(coord, 'execute_task_with_image'):
            result = await coord.execute_task_with_image(content, media_data)
            return {"response": result}
        else:
            raise NotImplementedError("图片任务未实现")

    elif task_type == "audio":
        if not media_data:
            raise ValueError("缺少音频数据")
        if hasattr(coord, 'execute_task_with_audio'):
            result = await coord.execute_task_with_audio(content, media_data)
            return {"response": result}
        else:
            raise NotImplementedError("音频任务未实现")

    elif task_type == "video":
        if not media_data:
            raise ValueError("缺少视频数据")
        if hasattr(coord, 'execute_task_with_video'):
            result = await coord.execute_task_with_video(content, media_data)
            return {"response": result}
        else:
            raise NotImplementedError("视频任务未实现")

    else:
        raise ValueError(f"不支持的任务类型: {task_type}")
