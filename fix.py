# fix.py
p = 'static/index.html'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 强行给我们的外部 API 菜单加上小箭头
old_html = '<div class="side-menu-item" id="menu-external-api" onclick="window.openSasesExternalApi && window.openSasesExternalApi()">\n            <span class="menu-icon">🔌</span>\n            <span>我的外部 API</span>\n          </div>'
new_html = '<div class="side-menu-item" id="menu-external-api" onclick="window.openSasesExternalApi && window.openSasesExternalApi()">\n            <span class="menu-icon">🔌</span>\n            <span>我的外部 API</span>\n            <span class="menu-arrow">›</span>\n          </div>'

# 兼容不同的缩进情况
if 'id="menu-external-api"' in c and '<span class="menu-arrow">›</span>' not in c.split('id="menu-external-api"')[1].split('</div>')[0]:
    # 找到那个 div 并替换
    parts = c.split('id="menu-external-api"')
    # parts[1] 是它后面的内容
    subparts = parts[1].split('</div>', 1)
    parts[1] = subparts[0] + '\n            <span class="menu-arrow">›</span>\n          ' + subparts[1]
    c = 'id="menu-external-api"'.join(parts)

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print("✅ 箭头已补全！")
