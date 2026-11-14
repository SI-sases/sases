import os
import re
import sqlite3

# ================= 1. 挂载路由 =================
def fix_routes():
    # __init__.py
    p = "core/api_routes/__init__.py"
    c = open(p, "r", encoding="utf-8").read()
    if "user_api_routes" not in c:
        anchor = "from . import hive_task_routes"
        c = c.replace(anchor, anchor + "\nfrom . import user_api_routes")
        open(p, "w", encoding="utf-8").write(c)
        print("✅ 路由 __init__.py 已挂载")
        
    # bootstrap.py
    p = "core/bootstrap.py"
    c = open(p, "r", encoding="utf-8").read()
    if "user_api_routes.router" not in c:
        anchor = "app.include_router(group_routes.router)"
        c = c.replace(anchor, anchor + "\n    app.include_router(user_api_routes.router)")
        open(p, "w", encoding="utf-8").write(c)
        print("✅ bootstrap.py 路由已挂载")

# ================= 2. 前端 HTML 胶囊 =================
def fix_html():
    p = "static/index.html"
    c = open(p, "r", encoding="utf-8").read()
    if 'id="api-pill"' in c:
        c = re.sub(r'<div id="api-pill".*?</div>', '', c)
    
    match = re.search(r'(<span id="param-rounds"[^>]*>.*?</span>)', c)
    if match:
        pill = '\n            <div id="api-pill" class="param-pill" title="选择本次允许调用的外部 API" style="cursor:pointer; margin-left: 8px;">🔌 API</div>'
        c = c.replace(match.group(1), match.group(1) + pill)
        open(p, "w", encoding="utf-8").write(c)
        print("✅ index.html 胶囊已插入")

# ================= 3. 前端 ParamBar 弹窗 =================
def fix_param_bar():
    p = "static/modules/param_bar.js"
    c = open(p, "r", encoding="utf-8").read()
    if "window.__toggleApi" in c:
        return
    logic = """
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
          if (!data.apis || data.apis.length === 0) { menu.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">暂无外部 API (请先去侧边栏添加)</div>'; return; }
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
window.initApiPill = initApiPill;
"""
    c = c.replace("export function initParamBar() {", logic + "\nexport function initParamBar() {\n  window.initApiPill();")
    open(p, "w", encoding="utf-8").write(c)
    print("✅ param_bar.js 弹窗逻辑已注入")

# ================= 4. 前端 Sidebar 入口 =================
def fix_sidebar():
    p = "static/modules/sidebar.js"
    c = open(p, "r", encoding="utf-8").read()
    if "menu-external-api" not in c:
        logic = """
  const menuExternalApi = document.getElementById('menu-external-api');
  if (menuExternalApi) {
    menuExternalApi.addEventListener('click', () => {
      closeSideDrawer();
      if (typeof window.__openExternalApiPage === 'function') {
        window.__openExternalApiPage();
      }
    });
  }
"""
        idx = c.find("if (menuMiniApps) {")
        if idx != -1:
            c = c[:idx] + logic + "\n  " + c[idx:]
            open(p, "w", encoding="utf-8").write(c)
            print("✅ sidebar.js 入口已注入")

    # HTML 侧边栏菜单项补充
    p = "static/index.html"
    c = open(p, "r", encoding="utf-8").read()
    if 'id="menu-external-api"' not in c:
        anchor = '<div class="side-menu-item" id="menu-mini-apps">'
        match = re.search(r'<div class="side-menu-item" id="menu-mini-apps">.*?</div>', c, re.DOTALL)
        if match:
            menu = match.group(0)
            new_menu = menu + '\n          <div class="side-menu-item" id="menu-external-api">\n            <span class="menu-icon">🔌</span>\n            <span>外部 API</span>\n            <span class="menu-arrow">›</span>\n          </div>'
            c = c.replace(menu, new_menu)
            open(p, "w", encoding="utf-8").write(c)
            print("✅ index.html 侧边栏菜单已插入")

# ================= 5. 前端 Chat 透传 =================
def fix_chat():
    p = "static/modules/chat.js"
    c = open(p, "r", encoding="utf-8").read()
    if "enabled_api_ids" not in c:
        c = c.replace("await api.sendMessage({", "await api.sendMessage({\n      enabled_api_ids: window.currentSessionAPIs || [],")
        open(p, "w", encoding="utf-8").write(c)
        print("✅ chat.js 透传已注入")

# ================= 6. 后端透传 (message_routes, send, commander) =================
def fix_backend_passthrough():
    # 1. message_routes.py
    p = "core/api_routes/message_routes.py"
    c = open(p, "r", encoding="utf-8").read()
    if "enabled_api_ids" not in c:
        c = c.replace("class SendMessageRequest(BaseModel):", "class SendMessageRequest(BaseModel):\n    enabled_api_ids: list = None")
        # 寻找 send_message 路由，把参数传下去
        c = c.replace("async def send_message(body: SendMessageRequest", "async def send_message(body: SendMessageRequest")
        c = c.replace("mode=body.mode", "mode=body.mode,\n        enabled_api_ids=body.enabled_api_ids")
        open(p, "w", encoding="utf-8").write(c)
        print("✅ message_routes.py 透传已修改")

    # 2. send.py
    p = "core/services/message/send.py"
    c = open(p, "r", encoding="utf-8").read()
    if "enabled_api_ids" not in c:
        # 函数签名加参数
        c = c.replace("def send_message(user_id, content, conversation_id", "def send_message(user_id, content, conversation_id, enabled_api_ids=None")
        # 传给 plan_task
        c = c.replace("supervisor_run_id=_run_id,", "supervisor_run_id=_run_id,\n                            enabled_api_ids=enabled_api_ids,")
        open(p, "w", encoding="utf-8").write(c)
        print("✅ send.py 透传已修改")

    # 3. commander.py
    p = "core/services/swarm/commander.py"
    c = open(p, "r", encoding="utf-8").read()
    if "enabled_api_ids" not in c:
        c = c.replace("max_steps: int = None\n) -> Dict[str, Any]:", "max_steps: int = None,\n    enabled_api_ids: list = None\n) -> Dict[str, Any]:")
        # 在查工具列表时过滤
        anchor = "_tools = _hr.harness_runtime.list_tools()"
        if anchor in c:
            new_anchor = """_tools = _hr.harness_runtime.list_tools()
        if enabled_api_ids:
            _tools = [t for t in _tools if t.get('id') in enabled_api_ids or f"ext_api_{t.get('id')}" in enabled_api_ids]"""
            c = c.replace(anchor, new_anchor)
        open(p, "w", encoding="utf-8").write(c)
        print("✅ commander.py 动态过滤已修改")

fix_routes()
fix_html()
fix_param_bar()
fix_sidebar()
fix_chat()
fix_backend_passthrough()
print("\n🎉 所有修复已完成！请重启服务并强制刷新浏览器。")