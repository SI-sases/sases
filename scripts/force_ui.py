import os

def inject_ui():
    # 1. 补充 param_bar.js 的胶囊弹窗逻辑
    p_param = "static/modules/param_bar.js"
    c_param = open(p_param, "r", encoding="utf-8").read()
    if "window.__toggleApi" not in c_param:
        logic = """
// ===== 🔌 API 胶囊逻辑 =====
export function initApiPill() {
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
      menu.className = 'param-menu show';
      menu.style.width = '240px'; menu.style.maxHeight = '300px'; menu.style.overflowY = 'auto';
      var rect = apiPill.getBoundingClientRect();
      menu.style.left = rect.left + 'px'; menu.style.bottom = (window.innerHeight - rect.top + 5) + 'px'; menu.style.top = 'auto';
      menu.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">加载中...</div>';
      document.body.appendChild(menu);
      fetch('/api/user-api/list', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') } })
        .then(r => r.json()).then(data => {
          if (!data.apis || data.apis.length === 0) { menu.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">暂无外部 API</div>'; return; }
          var html = '';
          data.apis.forEach(function(a) {
            var checked = (window.currentSessionAPIs || []).indexOf('ext_api_' + a.id) !== -1 ? 'checked' : '';
            html += '<label style="display:flex; align-items:center; padding:8px 12px; cursor:pointer;"><input type="checkbox" ' + checked + ' onchange="window.__toggleApi(\\'ext_api_' + a.id + '\\')" style="margin-right:8px;"><div><div style="font-size:14px;">' + a.api_name + '</div><div style="font-size:11px; color:#999;">' + a.method + ' ' + a.endpoint + '</div></div></label>';
          });
          menu.innerHTML = html;
        });
    };
  }
  if (!window._apiGlobalBound) {
    window._apiGlobalBound = true;
    document.addEventListener('click', function(e) {
      var menu = document.getElementById('api-menu');
      if (menu && !menu.contains(e.target) && e.target.id !== 'api-pill') menu.remove();
    });
  }
}
// 挂载到全局并强行调用
window.initApiPill = initApiPill;
setTimeout(function() { window.initApiPill(); }, 500);
"""
        c_param += logic
        open(p_param, "w", encoding="utf-8").write(c_param)
        print("✅ param_bar.js 弹窗逻辑已强行注入")
    else:
        print("✅ param_bar.js 弹窗逻辑已存在")

    # 2. 补充 sidebar.js 的点击绑定
    p_side = "static/modules/sidebar.js"
    c_side = open(p_side, "r", encoding="utf-8").read()
    if "menu-external-api" not in c_side:
        logic_side = """
  const menuExternalApi = document.getElementById('menu-external-api');
  if (menuExternalApi) {
    menuExternalApi.addEventListener('click', () => {
      closeSideDrawer();
      if (typeof window.__openExternalApiPage === 'function') {
        window.__openExternalApiPage();
      } else {
        console.error('openExternalApiPage not defined');
      }
    });
  }
"""
        idx = c_side.find("if (menuMiniApps) {")
        if idx != -1:
            c_side = c_side[:idx] + logic_side + "\n  " + c_side[idx:]
            open(p_side, "w", encoding="utf-8").write(c_side)
            print("✅ sidebar.js 点击绑定已注入")
    else:
        print("✅ sidebar.js 点击绑定已存在")

if __name__ == "__main__":
    inject_ui()