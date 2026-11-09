import re
from typing import Dict, Any, Optional

from core.harness_runtime import harness_runtime
from core import seed_utils
from core import config
from core import auth_service

def _keyword_match_tool(query: str):
    tools = harness_runtime.list_tools()
    query_lower = query.lower()

    for tool in tools:
        for cap in tool.capabilities:
            if cap.lower() in query_lower:
                return tool.module_id
        if tool.name.lower() in query_lower:
            return tool.module_id
        if tool.description.lower() in query_lower:
            return tool.module_id

    if "摄氏" in query and ("华氏" in query or "fahrenheit" in query_lower):
        return "unit-converter"
    if "华氏" in query and ("摄氏" in query or "celsius" in query_lower):
        return "unit-converter"
    if "温度" in query and "转换" in query:
        return "unit-converter"

    return None

def _llm_select_tool(query: str, user_id=None) -> Optional[str]:
    tools = harness_runtime.list_tools()
    if not tools:
        return None

    tool_descriptions = []
    for tool in tools:
        tool_descriptions.append(f"- {tool.module_id}: {tool.name} - {tool.description} (能力: {', '.join(tool.capabilities)})")
    tools_text = "\n".join(tool_descriptions)

    prompt = f"""你是 SASES 的工具选择器。根据用户任务，从下面的工具列表中选择最合适的一个工具来完成任务。
如果都不合适，返回 "none"。

工具列表：
{tools_text}

用户任务：
{query}

请只回复工具 ID，不要附加其他文字。"""
    try:
        response = seed_utils.call_chat(prompt, temperature=0.0, user_id=user_id)
        selected = response.strip().lower()
        if selected == "none":
            return None
        for tool in tools:
            if tool.module_id == selected:
                return selected
        return None
    except Exception as e:
        print(f"LLM 工具选择失败: {e}")
        return None

def _extract_params_for_tool(query: str, module_id: str) -> Optional[Dict[str, Any]]:
    if module_id == "unit-converter":
        match = re.search(r'[-+]?\d+(?:\.\d+)?', query)
        if not match:
            return None
        value = float(match.group())

        if "摄氏" in query and "华氏" in query:
            if query.index("摄氏") < query.index("华氏"):
                return {"celsius": value}
            else:
                return {"fahrenheit": value}
        elif "摄氏" in query:
            return {"celsius": value}
        elif "华氏" in query:
            return {"fahrenheit": value}
        else:
            return None
    else:
        return {"query": query}

def quick_execute(query: str) -> Optional[Dict[str, Any]]:
    module_id = _keyword_match_tool(query)
    if module_id is None:
        return None

    params = _extract_params_for_tool(query, module_id)
    if params is None:
        return None

    response = harness_runtime.invoke_tool(module_id, params)
    if response.success:
        return {
            "success": True,
            "message": "任务执行成功",
            "module_id": module_id,
            "result": response.result
        }
    else:
        return {
            "success": False,
            "message": response.error or "工具执行失败",
            "module_id": module_id,
            "result": None
        }

def execute_task(query: str, params: Optional[Dict[str, Any]] = None, user_id=None) -> Dict[str, Any]:
    if params is None:
        params = {}

    quick_result = quick_execute(query)
    if quick_result and quick_result["success"]:
        return quick_result

    module_id = _llm_select_tool(query, user_id=user_id)
    if module_id is None:
        return {
            "success": False,
            "message": "没有找到合适的工具来处理这个任务。",
            "module_id": None,
            "result": None
        }

    if not params:
        extracted = _extract_params_for_tool(query, module_id)
        if extracted is None:
            return {
                "success": False,
                "message": "无法从任务描述中提取参数，请提供更明确的信息。",
                "module_id": module_id,
                "result": None
            }
        params = extracted

    response = harness_runtime.invoke_tool(module_id, params)
    if response.success:
        return {
            "success": True,
            "message": "任务执行成功",
            "module_id": module_id,
            "result": response.result
        }
    else:
        return {
            "success": False,
            "message": response.error or "工具执行失败",
            "module_id": module_id,
            "result": None
        }

def execute_task_with_image(query: str, image_base64: str, user_id=None) -> Dict[str, Any]:
    if user_id is not None:
        api_keys = auth_service.get_active_api_keys(user_id)
        has_vision = False
        for entry in api_keys:
            provider = config.PROVIDER_ALIASES.get(entry["provider"], entry["provider"])
            vision_cfg = config.VISION_MODEL_BY_PROVIDER.get(provider)
            if vision_cfg and vision_cfg.get("supports_image"):
                has_vision = True
                break
        if not has_vision:
            return {
                "success": False,
                "message": "您没有配置支持图片的视觉模型 API Key，请先添加（如 DeepSeek 视觉模型或 OpenAI GPT-4o）",
                "module_id": None,
                "result": None
            }

    try:
        answer = seed_utils.call_chat(
            query,
            image_base64=image_base64,
            user_id=user_id,
            temperature=0.3
        )
        return {"success": True, "message": "多模态任务执行成功", "module_id": None, "result": {"answer": answer}}
    except Exception as e:
        return {"success": False, "message": f"多模态任务执行失败: {e}", "module_id": None, "result": None}

def execute_task_with_audio(query: str, audio_base64: str, user_id=None) -> Dict[str, Any]:
    return {"success": False, "message": "音频识别功能尚未接入，请使用文本或图片输入。", "module_id": None, "result": None}

def execute_task_with_video(query: str, video_base64: str, user_id=None) -> Dict[str, Any]:
    return {"success": False, "message": "视频理解功能尚未接入，请使用文本或图片输入。", "module_id": None, "result": None}
