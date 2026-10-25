import os
import subprocess

print("=== 1. 检查积分提示代码 ===")
path = 'core/services/supervisor/continuation.py'
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

if '系统提示：您的积分不足' not in code:
    print("⚠️ 发现积分提示丢失，正在安全修复...")
    # 在 finish_run(run_id, status='insufficient_credits') 前安全注入
    inject = """            try:
                with db_cursor(commit=True) as _c_c:
                    _c_c.execute("INSERT INTO messages (conversation_id, sender, content, msg_type) VALUES (?, 'assistant', '⚠️ 系统提示：您的积分不足，任务已终止。', 'standard')", (conversation_id,))
            except: pass
            finish_run(run_id, status='insufficient_credits')"""
    code = code.replace("finish_run(run_id, status='insufficient_credits')", inject)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code)
    print("✅ 积分提示已安全修复。")
else:
    print("☑️ 积分提示已存在。")

print("\n=== 2. 检查打包脚本是否包含危险文件 ===")
build_path = 'scripts/build_portable.py'
with open(build_path, 'r', encoding='utf-8') as f:
    build_code = f.read()

if '".env"' in build_code:
    print("❌ 危险：打包脚本包含了 .env 文件！正在移除...")
    build_code = build_code.replace('".env",', '')
    with open(build_path, 'w', encoding='utf-8') as f:
        f.write(build_code)
    print("✅ 已从打包列表中剔除 .env。")
else:
    print("☑️ 打包列表未包含本地 .env，很安全。")

print("\n=== 3. 生成热更新小包 code_update.zip ===")
import zipfile
update_zip = 'static/downloads/code_update.zip'
with zipfile.ZipFile(update_zip, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('core'):
        for file in files:
            if '__pycache__' not in root and file.endswith('.py'):
                z.write(os.path.join(root, file))
    z.write('app_full.py')
    z.write('requirements.txt')
print("✅ code_update.zip 生成成功！")
