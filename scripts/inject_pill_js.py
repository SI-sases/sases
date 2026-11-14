import os

p = "static/index.html"
c = open(p, "r", encoding="utf-8").read()

if "api_pill.js" not in c:
    # 找 </body> 标签，把 script 插进去
    c = c.replace("</body>", '  <script src="/static/modules/api_pill.js"></script>\n</body>')
    open(p, "w", encoding="utf-8").write(c)
    print("✅ 胶囊独立脚本已成功引入 index.html")
else:
    print("✅ 脚本已存在，无需重复引入")