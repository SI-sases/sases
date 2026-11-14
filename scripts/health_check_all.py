import os
import sqlite3
import subprocess

def check_item(name, condition, detail=""):
    if condition:
        print(f"✅ [{name}] 正常 {detail}")
    else:
        print(f"❌ [{name}] 缺失或损坏 {detail}")

def check_file_content(filepath, keywords):
    if not os.path.exists(filepath):
        return False, "文件不存在"
    content = open(filepath, "r", encoding="utf-8").read()
    missing = [k for k in keywords if k not in content]
    if missing:
        return False, f"缺少关键代码: {missing}"
    return True, ""

def main():
    print("========== SASES 全系统体检报告 ==========\n")

    # 1. 检查 A2A (好友智能体)
    print("--- 1. A2A 好友智能体模块 ---")
    check_item("后端拦截文件", os.path.exists("core/services/friend_gate.py"))
    check_item("跨端投递文件", os.path.exists("core/services/cross_account_delivery.py"))
    
    ok, msg = check_file_content("core/services/message/send.py", ["check_friend_gate"])
    check_item("send.py 拦截注入", ok, msg)
    
    ok, msg = check_file_content("core/services/supervisor/runs.py", ["deliver_to_linked_accounts"])
    check_item("runs.py 结果回传", ok, msg)
    
    ok, msg = check_file_content("static/modules/chat.js", ["showProposedRunCard", "friend-mode-btn"])
    check_item("前端黄卡与模式切换", ok, msg)

    # 2. 检查 P0-P2 地基 (API 胶囊与分发)
    print("\n--- 2. 地基底座 (P0-P2) ---")
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('api_registry', 'scheduled_tasks', 'supervisor_runs', 'user_api_configs', 'license_keys')")
    tables = [r[0] for r in cur.fetchall()]
    check_item("核心数据库表", len(tables) == 5, f"已建表: {tables}")
    
    ok, msg = check_file_content("core/harness_runtime.py", ["_invoke_tool_legacy", "api_category"])
    check_item("工具分类分派 (render)", ok, msg)
    
    ok, msg = check_file_content("core/api_routes/scheduled_routes.py", ["router"])
    check_item("定时任务路由", ok, msg)

    # 3. 检查 CDK 商业化
    print("\n--- 3. CDK 商业化闭环 ---")
    ok, msg = check_file_content("core/services/message/send.py", ["P0-D: 付费墙预检"])
    check_item("L1 本地拦截", ok, msg)
    
    ok, msg = check_file_content("core/api_routes/harness_routes.py", ["verify_exec_token"])
    check_item("L3 执行门禁", ok, msg)
    
    check_item("Ed25519 私钥", os.path.exists("core/keys/license_priv.pem"))
    check_item("Ed25519 公钥", os.path.exists("core/keys/license_pub.pem"))

    # 4. 检查外部 API 闭环
    print("\n--- 4. 外部 API 闭环 ---")
    ok, msg = check_file_content("core/services/swarm/commander.py", ["enabled_api_ids"])
    check_item("指挥官工具过滤", ok, msg)
    
    ok, msg = check_file_content("static/modules/param_bar.js", ["__toggleApi"])
    check_item("前端 API 胶囊弹窗", ok, msg)
    
    ok, msg = check_file_content("core/api_routes/user_api_routes.py", ["api_registry"])
    check_item("外部 API 自动注册", ok, msg)

    # 5. 检查启动器与打包
    print("\n--- 5. 启动器与打包 ---")
    check_item("启动器硬件指纹", os.path.exists("launcher/hardware.py"))
    check_item("启动器卡密弹窗", os.path.exists("launcher/ui/license_dialog.py"))
    ok, msg = check_file_content("scripts/build_portable.py", ["ignore_patterns"])
    check_item("打包防泄密过滤", ok, msg)

    print("\n==========================================")
    conn.close()

if __name__ == "__main__":
    main()