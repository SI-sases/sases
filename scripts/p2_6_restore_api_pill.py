import os
import shutil
from datetime import datetime

HTML = "static/index.html"
PARAM_JS = "static/modules/param_bar.js"
CHAT_JS = "static/modules/chat.js"

# ---------- 1. index.html 补回 api-pill ----------
HTML_OLD = '''            <span id="param-rounds" class="param-pill" title="点击设置本轮最大步数">⚙ 8步</span>
          </div>'''
HTML_NEW = '''            <span id="param-rounds" class="param-pill" title="点击设置本轮最大步数">⚙ 8步</span>
            <div id="api-pill" class="param-pill" title="选择本次允许调用的外部 API" style="cursor:pointer;">🔌 API</div>
          </div>'''

# ---------- 2. param_bar.js 补回 API 逻辑 ----------
# 在 initParamBar 函数的最前面插入
PARAM_OLD = '''export function initParamBar() {
  _currentValue = _read();'''
PARAM_NEW = '''export function initParamBar() {
  // ===== 🔌 API 胶囊逻辑 =====
  window.currentSessionAPIs = window.currentSessionAPIs || [];
  
  window.__toggleApi = function(id) {
    var set = new Set(window.currentSessionAPIs);
    if (set.has(id)) set.delete(id); else set.add(id);
    window.currentSessionAPIs = Array.from(set);
    var p = document.getElementById('api-pill');
    if (p) p.innerText = window.currentSessionAPIs.length > 0 ? ('🔌 API (' + window.currentSessionAPIs.length + ')') : '🔌 API';
  };

  var apiPill = document.getElementById('api-pill');
  if (apiPill && !apiPill._bound) {
    apiPill._bound = true;
    apiPill.onclick = function(e) {
      e.stopPropagation();
      var menu = document.getElementById('api-menu');
      if (menu) { menu.remove(); return; }
      
      menu = document.createElement('div');
      menu.id = 'api-menu';
      menu.className = 'param-menu show'; // 复用 param-menu 的样式
      menu.style.width = '240px';
      menu.style.maxHeight = '300px';
      menu.style.overflowY = 'auto';
      
      var rect = apiPill.getBoundingClientRect();
      menu.style.left = rect.left + 'px';
      menu.style.bottom = (window.innerHeight - rect.top + 5) + 'px';
      menu.style.top = 'auto';
      menu.innerHTML = '<div style="padding: 10px; color: #999; font-size: 12px; text-align: center;">加载中...</div>';
      document.body.appendChild(menu);

      // 加载用户外部 API 列表
      var token = localStorage.getItem('sases_token');
      fetch('/api/user-api/list', { headers: { 'Authorization': 'Bearer ' + token } })
        .then(r => r.json())
        .then(data => {
          if (!data.apis || data.apis.length === 0) {
            menu.innerHTML = '<div style="padding: 10px; color: #999; font-size: 12px; text-align: center;">暂无外部 API 配置</div>';
            return;
          }
          var html = '';
          data.apis.forEach(function(a) {
            var checked = (window.currentSessionAPIs || []).indexOf('ext_api_' + a.id) !== -1 ? 'checked' : '';
            html += '<label style="display:flex; align-items:center; padding:8px 12px; cursor:pointer;">' +
                    '<input type="checkbox" ' + checked + ' onchange="window.__toggleApi(\\'ext_api_' + a.id + '\\')" style="margin-right:8px;">' +
                    '<div><div style="font-size:14px; color:#333;">' + a.api_name + '</div>' +
                    '<div style="font-size:11px; color:#999;">' + a.method + ' ' + a.endpoint + '</div></div>' +
                    '</label>';
          });
          menu.innerHTML = html;
        })
        .catch(e => {
          menu.innerHTML = '<div style="padding: 10px; color: #ff3b30; font-size: 12px; text-align: center;">加载失败</div>';
        });
    };
  }
  
  if (!window._sasesApiGlobalBound) {
    window._sasesApiGlobalBound = true;
    document.addEventListener('click', function(e) {
      var menu = document.getElementById('api-menu');
      if (menu && !menu.contains(e.target) && e.target.id !== 'api-pill') {
        menu.remove();
      }
    });
  }
  // ===== API 逻辑结束 =====

  _currentValue = _read();'''

# ---------- 3. chat.js 补回 enabled_api_ids ----------
# 由于有 4 处 sendMessage，我们靠特征查找：包含 payload 和 content 的那处
CHAT_MARKERS = [
    ("await api.sendMessage({", "await api.sendMessage({\n          enabled_api_ids: window.currentSessionAPIs || [],"),
    ("const data = await api.sendMessage({", "const data = await api.sendMessage({\n      enabled_api_ids: window.currentSessionAPIs || [],")
]


def patch_html():
    if not os.path.exists(HTML): return
    c = open(HTML, "r", encoding="utf-8").read()
    if 'id="api-pill"' in c:
        print("index.html: api-pill already exists")
        return
    if HTML_OLD not in c:
        print("ERROR: index.html anchor not found")
        return
    shutil.copy2(HTML, HTML + ".bak_api_" + datetime.now().strftime("%H%M%S"))
    c = c.replace(HTML_OLD, HTML_NEW, 1)
    open(HTML, "w", encoding="utf-8").write(c)
    print("index.html: api-pill restored")

def patch_param():
    if not os.path.exists(PARAM_JS): return
    c = open(PARAM_JS, "r", encoding="utf-8").read()
    if "window.__toggleApi" in c:
        print("param_bar.js: API logic already exists")
        return
    if PARAM_OLD not in c:
        print("ERROR: param_bar.js anchor not found")
        return
    shutil.copy2(PARAM_JS, PARAM_JS + ".bak_api_" + datetime.now().strftime("%H%M%S"))
    c = c.replace(PARAM_OLD, PARAM_NEW, 1)
    open(PARAM_JS, "w", encoding="utf-8").write(c)
    print("param_bar.js: API logic restored")

def patch_chat():
    if not os.path.exists(CHAT_JS): return
    c = open(CHAT_JS, "r", encoding="utf-8").read()
    if "enabled_api_ids:" in c:
        print("chat.js: enabled_api_ids already exists")
        return
    
    patched = 0
    for old, new in CHAT_MARKERS:
        if old in c:
            c = c.replace(old, new, 1)
            patched += 1
    
    if patched > 0:
        shutil.copy2(CHAT_JS, CHAT_JS + ".bak_api_" + datetime.now().strftime("%H%M%S"))
        open(CHAT_JS, "w", encoding="utf-8").write(c)
        print("chat.js: enabled_api_ids restored (matched " + str(patched) + " places)")
    else:
        print("WARN: chat.js sendMessage anchor not found")

if __name__ == "__main__":
    patch_html()
    patch_param()
    patch_chat()