import os
import shutil
from datetime import datetime

def run(params):
    file_path = params.get("file_path")
    if not file_path:
        return {"success": False, "error": "缺少 file_path"}
        
    create_if_missing = params.get("create_if_missing", False)
    if not os.path.exists(file_path):
        if create_if_missing:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("")
        else:
            return {"success": False, "error": f"文件不存在: {file_path}"}

    # 自动备份
    backup_dir = os.path.join(os.path.dirname(file_path), ".backups")
    os.makedirs(backup_dir, exist_ok=True)
    safe_name = os.path.basename(file_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = os.path.join(backup_dir, f"{safe_name}.{ts}.bak")
    shutil.copy2(file_path, backup_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        original = f.read()
        
    new_content = None  # 👈 终极防弹：提前初始化变量！

    try:
        if params.get("overwrite") is True:
            new_content = params.get("new_content", "")
            
        elif params.get("old_snippet") is not None:
            old = params.get("old_snippet")
            new = params.get("new_snippet", "")
            if old not in original:
                return {"success": False, "error": f"原片段未找到"}
            new_content = original.replace(old, new, 1)
            
        elif params.get("anchor_pattern") is not None:
            anchor = params.get("anchor_pattern")
            position = params.get("position", "after")
            insert_text = params.get("new_content", "")
            
            if anchor not in original:
                return {"success": False, "error": f"锚点未找到: {anchor}"}
                
            if position == "before":
                new_content = original.replace(anchor, insert_text + chr(10) + anchor, 1)
            elif position == "after":
                new_content = original.replace(anchor, anchor + chr(10) + insert_text, 1)
            elif position == "replace_line":
                lines = original.split(chr(10))
                for i, line in enumerate(lines):
                    if anchor in line:
                        lines[i] = insert_text
                        break
                new_content = chr(10).join(lines)
        else:
            return {"success": False, "error": "未提供修改模式"}

        if new_content is not None:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return {"success": True, "message": "修改成功"}
        else:
            return {"success": False, "error": "生成新内容失败"}

    except Exception as e:
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
        return {"success": False, "error": f"执行异常并已回滚: {str(e)}"}
