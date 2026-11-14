import os
import re

def add_api_ui():
    print("🛠 正在注入前端 UI...")
    
    # 1. index.html 注入胶囊和侧边栏
    p_html = "static/index.html"
    c = open(p_html, "r", encoding="utf-8").read()
    if 'id="api-pill"' not in c:
        # 用正则找 param-rounds，插入胶囊
        match = re.search(r'(<span id="param-rounds".*?</span>)', c)
        if match:
            c = c.replace(match.group(1), match.group(1) + '\n            <div id="api-pill" class="param-pill" title="选择外部 API" style="cursor:pointer; margin-left: 8px;">🔌 API</div>')
        # 找 menu-mini-apps，插入侧边栏
        match_menu = re.search(r'<div class="side-menu-item" id="menu-mini-apps">.*?</div>', c, re.DOTALL)
        if match_menu:
            c = c.replace(match_menu.group(0), match_menu.group(0) + '\n          <div class="side-menu-item" id="menu-external-api">\n            <span class="menu-icon">🔌</span>\n            <span>外部 API</span>\n            <span class="menu-arrow">›</span>\n          </div>')
        open(p_html, "w", encoding="utf-8").write(c)
        print("✅ 1. index.html 胶囊和外部 API 入口已注入")

    # 2. 从 0c56e67 提取 me_external_api.js 和 param_bar.js 的弹窗逻辑
    os.system("git show 0c56e67:static/modules/me_external_api.js > static/modules/me_external_api.js")
    
    # 在 index.html 引入 me_external_api.js
    if 'me_external_api.js' not in c:
        c = c.replace('</body>', '  <script src="/static/modules/me_external_api.js"></script>\n</body>')
        open(p_html, "w", encoding="utf-8").write(c)
        print("✅ 2. external_api 脚本已引入")
        
    # 3. param_bar.js 注入胶囊点击逻辑
    p_param = "static/modules/param_bar.js"
    c_param = open(p_param, "r", encoding="utf-8").read()
    if "window.__toggleApi" not in c_param:
        # (这里使用之前写好的完美弹窗逻辑)
        logic = """\nexport function initApiPill() { ... window.initApiPill = initApiPill;\n"""
        # (为了省篇幅，直接调用 0c56e67 的代码)
        os.system("git show 0c56e67:static/modules/param_bar.js > temp_param.js")
        temp_c = open("temp_param.js", "r", encoding="utf-8").read()
        match_api = re.search(r'(// ===== 🔌 API 胶囊逻辑.*?// ===== API 逻辑结束 =====)', temp_c, re.DOTALL)
        if match_api:
            c_param = c_param.replace("export function initParamBar() {", match_api.group(1) + "\nexport function initParamBar() {\n  window.initApiPill();")
            open(p_param, "w", encoding="utf-8").write(c_param)
            print("✅ 3. param_bar.js 胶囊逻辑已注入")
        os.remove("temp_param.js")

add_api_ui()