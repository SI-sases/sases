import json

def run(params):
    json_string = params.get("json_string", "")
    indent = params.get("indent", 2)
    if not json_string:
        raise ValueError("缺少 json_string 参数")
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")
    if indent is None or indent <= 0:
        formatted = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    else:
        formatted = json.dumps(data, ensure_ascii=False, indent=indent)
    return {"formatted": formatted}
