import base64

def run(params):
    action = params.get("action", "")
    text = params.get("text", "")
    if action == "encode":
        result = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    elif action == "decode":
        try:
            result = base64.b64decode(text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Base64 解码失败: {e}")
    else:
        raise ValueError("action 必须是 encode 或 decode")
    return {"result": result}
