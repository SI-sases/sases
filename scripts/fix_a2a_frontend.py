import subprocess
import re

def get_file_at_commit(commit, path):
    res = subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, text=True, encoding="utf-8")
    return res.stdout

def main():
    p = "static/modules/chat.js"
    c = open(p, "r", encoding="utf-8").read()
    old = get_file_at_commit("p2-a2a-completed", p)

    # 1. 提取 showProposedRunCard 函数（如果当前没有）
    if "function showProposedRunCard" not in c:
        match = re.search(r'(function showProposedRunCard\(runId\) \{.*?\n\})', old, re.DOTALL)
        if match:
            c += "\n" + match.group(1)
            print("✅ showProposedRunCard 已注入")

    # 2. 提取 WS 的 proposed_run_id 监听
    if "showProposedRunCard(d.proposed_run_id)" not in c:
        anchor = "const data = JSON.parse(event.data);"
        if anchor in c:
            c = c.replace(anchor, anchor + "\n    if (data.proposed_run_id) { showProposedRunCard(data.proposed_run_id); }")
            print("✅ WS 黄卡监听已注入")

    # 3. 提取身份模式切换按钮
    if "friend-mode-btn" not in c:
        match = re.search(r'(const oldBtn = document\.getElementById\(\'friend-mode-btn\'\).*?\n  \})', old, re.DOTALL)
        if match:
            # 插在 openChatWindow 结尾
            c = c.replace("function openChatWindow(", match.group(1) + "\nfunction openChatWindow(")
            print("✅ 模式切换按钮已注入")

    open(p, "w", encoding="utf-8").write(c)

if __name__ == "__main__":
    main()