import subprocess
import os

def get_file_at_commit(commit, path):
    res = subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, text=True, encoding="utf-8")
    return res.stdout

def main():
    # 1. 修复 send.py 的拦截逻辑
    p_send = "core/services/message/send.py"
    c_send = open(p_send, "r", encoding="utf-8").read()
    old_send = get_file_at_commit("p2-a2a-completed", p_send)
    
    # 提取原版 693 行附近的 friend_gate 逻辑（包含触发提案的完整块）
    import re
    match = re.search(r'(from core\.services\.friend_gate import check_friend_gate.*?if _gate_res\.get\("action"\) == "block":.*?\n)', old_send, re.DOTALL)
    if match:
        logic = match.group(1)
        # 移除我们之前错误注入的残缺逻辑
        c_send = re.sub(r'_gate = check_friend_gate\(.*?return \{\n.*?\n    \}\n', '', c_send, flags=re.DOTALL)
        # 插入正确逻辑（插在 _scan_content 之前）
        anchor = "_scan_content = _normalize_prefix(content)"
        if "from core.services.friend_gate import check_friend_gate" not in c_send:
            c_send = c_send.replace(anchor, logic + "\n    " + anchor)
            open(p_send, "w", encoding="utf-8").write(c_send)
            print("✅ send.py A2A 标准拦截已修复")
    
    # 2. 修复 runs.py 的回传逻辑
    p_runs = "core/services/supervisor/runs.py"
    c_runs = open(p_runs, "r", encoding="utf-8").read()
    old_runs = get_file_at_commit("p2-a2a-completed", p_runs)
    
    # 提取原版 190 行附近的 deliver_to_linked_accounts 逻辑
    match = re.search(r'(from \.\.cross_account_delivery import deliver_to_linked_accounts.*?\n.*?deliver_to_linked_accounts\(.*?\n.*?\))', old_runs, re.DOTALL)
    if match and "deliver_to_linked_accounts" not in c_runs:
        logic = match.group(1)
        # 插在 finish_run 的成功结尾处
        anchor = "if status == 'completed':"
        if anchor in c_runs:
            c_runs = c_runs.replace(anchor, anchor + "\n            " + logic.replace("\n", "\n            "))
            open(p_runs, "w", encoding="utf-8").write(c_runs)
            print("✅ runs.py A2A 回传已注入")

if __name__ == "__main__":
    main()