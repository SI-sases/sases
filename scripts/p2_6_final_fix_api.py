import os
import shutil
from datetime import datetime

HTML = "static/index.html"
SIDEBAR_JS = "static/modules/sidebar.js"

def main():
    # --- 1. 修复 index.html (API 胶囊 + 引入 external_api.js) ---
    c_html = open(HTML, "r", encoding="utf-8").read()
    ts = datetime.now().strftime("%H%M%S")
    
    # 1.1 插入 API 胶囊 (用正则/更宽的锚点，无视乱码)
    if 'id="api-pill"' not in c_html:
        anchor = '<div id="param-bar" class="param-bar">'
        if anchor in c_html:
            # 直接在 param-bar 后面插入胶囊，不用管原来的 8步 是什么乱码
            new_html = anchor + '\n            <div id="api-pill" class="param-pill" title="选择本次允许调用的外部 API" style="cursor:pointer; margin-left: 8px;">🔌 API</div>'
            c_html = c_html.replace(anchor, new_html, 1)
            print("index.html: api-pill 插入成功")
        else:
            print("ERROR: 找不到 param-bar 锚点")
    else:
        print("index.html: api-pill 已存在")

    # 1.2 引入 external_api.js
    if "external_api.js" not in c_html:
        # 找底部的 script 标签，插在 main.js 前面
        import re
        # 假设引入格式类似 <script src="/static/modules/main.js" ...
        # 我们在 body 结束前插入
        anchor_script = '<script src="/static/modules/main.js"'
        if anchor_script in c_html:
            c_html = c_html.replace(anchor_script, '<script src="/static/external_api.js"></script>\n  ' + anchor_script, 1)
            print("index.html: external_api.js 引入成功")
        else:
            # 兜底：直接插在 </body> 前
            if "</body>" in c_html:
                c_html = c_html.replace("</body>", '  <script src="/static/external_api.js"></script>\n</body>', 1)
                print("index.html: external_api.js 兜底引入成功")
            else:
                print("ERROR: 找不到 </body> 或 script 锚点")
    else:
        print("index.html: external_api.js 已引入")

    open(HTML, "w", encoding="utf-8").write(c_html)
    shutil.copy2(HTML, HTML + ".bak_final_" + ts)

    # --- 2. 修复 sidebar.js 绑定 ---
    c_js = open(SIDEBAR_JS, "r", encoding="utf-8").read()
    if "openSasesExternalApi" not in c_js:
        # 替换之前写错的 __openExternalApiPage
        c_js = c_js.replace("typeof window.__openExternalApiPage === 'function'", "typeof window.openSasesExternalApi === 'function'")
        c_js = c_js.replace("window.__openExternalApiPage();", "window.openSasesExternalApi();")
        print("sidebar.js: 已修复为调用 openSasesExternalApi")
    else:
        print("sidebar.js: 已经是 openSasesExternalApi")
    
    open(SIDEBAR_JS, "w", encoding="utf-8").write(c_js)
    shutil.copy2(SIDEBAR_JS, SIDEBAR_JS + ".bak_final_" + ts)

if __name__ == "__main__":
    main()