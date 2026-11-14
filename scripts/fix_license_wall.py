import subprocess
import re

def main():
    p = "core/services/message/send.py"
    c = open(p, "r", encoding="utf-8").read()
    
    if "license_service" in c:
        print("✅ 已经存在 license 拦截")
        return
        
    old_send = subprocess.run(["git", "show", "772f05b:core/services/message/send.py"], capture_output=True, text=True, encoding="utf-8").stdout
    
    # 尝试提取 license 验证块
    # 通常是类似 if content.startswith("#1") ... 然后调用 license_service
    match = re.search(r'(if .*?#[1-4].*?:.*?license_service.*?\n.*?raise HTTPException.*?\n)', old_send, re.DOTALL)
    if not match:
        # 模糊匹配
        match = re.search(r'([ \t]+if .*startswith.*[\"\'#][1-4].*?\n(?:.*\n){0,5}.*?license.*?\n(?:.*\n){0,5}.*?return.*?\n)', old_send)
        
    if match:
        logic = match.group(1)
        # 找到插入点：通常在 _scan_content 处理之后，或者函数最前面
        anchor = "_scan_content = _normalize_prefix(content)"
        if anchor in c:
            c = c.replace(anchor, logic + "\n    " + anchor)
            open(p, "w", encoding="utf-8").write(c)
            print("✅ L1 付费墙拦截已精准注入")
        else:
            print("❌ 找不到插入点 _scan_content")
    else:
        print("❌ 在 772f05b 中没找到清晰的 license 拦截块，请把第一步的输出发给我")

if __name__ == "__main__":
    main()