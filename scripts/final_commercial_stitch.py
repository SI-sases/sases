import subprocess
import re

def get_file_at_commit(commit, path):
    res = subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, text=True, encoding="utf-8")
    return res.stdout

def main():
    print("🛠 开始执行《商业化闭环》全量缝合...")

    # ================= 1. 修补 L1 本地拦截 (send.py) =================
    p_send = "core/services/message/send.py"
    c_send = open(p_send, "r", encoding="utf-8").read()
    if "P0-D: 付费墙预检" not in c_send:
        old_send = get_file_at_commit("772f05b", p_send)  # 提取当年 P0-D 的代码
        match = re.search(r'(# ===== P0-D: 付费墙预检.*?)(?=\n\s*_scan_content)', old_send, re.DOTALL)
        if match:
            c_send = c_send.replace("_scan_content = _normalize_prefix(content)", match.group(1) + "\n\n    _scan_content = _normalize_prefix(content)")
            open(p_send, "w", encoding="utf-8").write(c_send)
            print("✅ L1 本地预检拦截已恢复 (send.py)")

    # ================= 2. 修补 L3 执行层门禁 (harness_routes.py) =================
    p_harness = "core/api_routes/harness_routes.py"
    c_harness = open(p_harness, "r", encoding="utf-8").read()
    if "verify_exec_token" not in c_harness:
        # 从 61d53eb（商业化封板版本）提取
        old_harness = get_file_at_commit("61d53eb", p_harness)
        match = re.search(r'(# ===== P0-E: /harness/execute 门禁.*?)(?=\s*try:)', old_harness, re.DOTALL)
        if match:
            c_harness = c_harness.replace("async def execute(body: ExecuteRequest, user_id: int = Depends(get_current_user)):", 
                                          "async def execute(body: ExecuteRequest, user_id: int = Depends(get_current_user)):\n" + match.group(1))
            open(p_harness, "w", encoding="utf-8").write(c_harness)
            print("✅ L3 执行层门禁已恢复 (harness_routes.py)")

    # ================= 3. 修补路由挂载 (bootstrap.py) =================
    p_boot = "core/bootstrap.py"
    c_boot = open(p_boot, "r", encoding="utf-8").read()
    if "license_routes.router" not in c_boot:
        c_boot = c_boot.replace("app.include_router(user_api_routes.router)", 
                                "from .api_routes import license_routes\n    app.include_router(license_routes.router)\n    app.include_router(user_api_routes.router)")
        open(p_boot, "w", encoding="utf-8").write(c_boot)
        print("✅ license_routes 路由已挂载 (bootstrap.py)")

    # ================= 4. 修补底层死循环 (decider.py) =================
    # 刚才查不到 task_summarizer，说明这个文件可能被严重覆盖，直接恢复历史版本
    p_decider = "core/services/supervisor/decider.py"
    if "task_summarizer" not in open(p_decider, "r", encoding="utf-8").read():
        subprocess.run(["git", "checkout", "61d53eb", "--", p_decider])
        print("✅ 底层多轮判定引擎已从 61d53eb 恢复 (decider.py)")

    # ================= 5. 修补底层多轮续跑 (continuation.py) =================
    p_cont = "core/services/supervisor/continuation.py"
    if "return True, build_next_input" not in open(p_cont, "r", encoding="utf-8").read():
        subprocess.run(["git", "checkout", "61d53eb", "--", p_cont])
        print("✅ 多轮续跑引擎已从 61d53eb 恢复 (continuation.py)")

    print("🎉 全量缝合执行完毕，请重启服务验证！")

if __name__ == "__main__":
    main()