# harness_modules/search_tools/main.py
"""P1.5：搜索扩展工具池（不把全部工具塞进主提示词）。"""


def run(params):
    q = str(params.get("query") or "").strip().lower()
    if not q:
        return {"success": False, "error": "缺少 query"}
    try:
        from core.harness_runtime import harness_runtime as hr
        tools = hr.list_all_tools()
    except Exception as e:
        return {"success": False, "error": "读取工具注册表失败: " + str(e)}

    hits = []
    for t in tools:
        text = (str(getattr(t, "module_id", "")) + " " + str(getattr(t, "name", "")) + " "
                + str(getattr(t, "description", "")) + " " + str(getattr(t, "category", ""))).lower()
        if q in text:
            hits.append({
                "id": t.module_id,
                "name": t.name,
                "desc": (t.description or "")[:160],
                "tier": getattr(t, "tier", "extension"),
                "category": getattr(t, "category", "general"),
            })
    hits.sort(key=lambda x: (x["tier"] != "extension", x["id"]))
    return {"success": True, "query": q, "count": len(hits), "tools": hits[:12],
            "hint": "选中后直接用 module_id 调用即可"}
