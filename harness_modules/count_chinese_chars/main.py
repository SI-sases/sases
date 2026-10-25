def run(params):
    import re
    text = params.get("text", "")
    cnt = len(re.findall(r"[一-鿿]", text))
    return {"success": True, "count": cnt}