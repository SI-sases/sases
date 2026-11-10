import json


def file_patch(file_path, old_snippet, new_snippet):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    if old_snippet not in content:
        return {"success": False, "error": "原片段未找到"}
    content = content.replace(old_snippet, new_snippet, 1)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "file_path": file_path}
