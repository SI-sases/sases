from harness_modules.file_patch.main import run as patch_run


def run(params):
    file_path = params.get("file_path")
    old_code = params.get("old_code")
    new_code = params.get("new_code")
    if not all([file_path, old_code, new_code]):
        return {"success": False, "error": "缺少 file_path, old_code 或 new_code"}
    patch_params = {
        "file_path": file_path,
        "old_snippet": old_code,
        "new_content": new_code,
        "expected_count": 1,
    }
    return patch_run(patch_params)
