// static/modules/api_pill.js
window.currentSessionAPIs = window.currentSessionAPIs || [];

window.__toggleApi = function(id) {
  var set = new Set(window.currentSessionAPIs);
  if (set.has(id)) set.delete(id); else set.add(id);
  window.currentSessionAPIs = Array.from(set);
  var p = document.getElementById('api-pill');
  if (p) p.innerText = window.currentSessionAPIs.length > 0 ? ('🔌 API (' + window.currentSessionAPIs.length + ')') : '🔌 API';
};

document.addEventListener('DOMContentLoaded', function() {
  // 1. 绑定胶囊事件
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
      menu.style.width = '240px'; 
      menu.style.maxHeight = '300px'; 
      menu.style.overflowY = 'auto';
      
      var rect = apiPill.getBoundingClientRect();
      menu.style.left = rect.left + 'px'; 
      menu.style.bottom = (window.innerHeight - rect.top + 5) + 'px'; 
      menu.style.top = 'auto';
      menu.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">加载中...</div>';
      document.body.appendChild(menu);
      
      fetch('/api/user-api/list', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') } })
        .then(r => r.json()).then(data => {
          if (!data.apis || data.apis.length === 0) { 
            menu.innerHTML = '<div style="padding: 10px; color: #999; text-align: center;">暂无外部 API</div>'; 
            return; 
          }
          var html = '';
          data.apis.forEach(function(a) {
            var checked = (window.currentSessionAPIs || []).indexOf('ext_api_' + a.id) !== -1 ? 'checked' : '';
            html += '<label style="display:flex; align-items:center; padding:8px 12px; cursor:pointer;">' +
                    '<input type="checkbox" ' + checked + ' onchange="window.__toggleApi(\'ext_api_' + a.id + '\')" style="margin-right:8px;">' +
                    '<div><div style="font-size:14px;">' + a.api_name + '</div>' +
                    '<div style="font-size:11px; color:#999;">' + a.method + ' ' + a.endpoint + '</div></div></label>';
          });
          menu.innerHTML = html;
        });
    };
  }
  
  // 2. 点击空白处关闭菜单
  if (!window._apiGlobalBound) {
    window._apiGlobalBound = true;
    document.addEventListener('click', function(e) {
      var menu = document.getElementById('api-menu');
      if (menu && !menu.contains(e.target) && e.target.id !== 'api-pill') menu.remove();
    });
  }

  // 3. 绑定侧边栏的外部 API 入口
  var menuExternalApi = document.getElementById('menu-external-api');
  if (menuExternalApi && !menuExternalApi._bound) {
    menuExternalApi._bound = true;
    menuExternalApi.addEventListener('click', function() {
      if (typeof window.closeSideDrawer === 'function') window.closeSideDrawer();
      var drawer = document.getElementById('side-drawer');
      if (drawer) {
        drawer.classList.remove('open');
        setTimeout(() => drawer.style.display = 'none', 300);
      }
      if (typeof window.__openExternalApiPage === 'function') {
        window.__openExternalApiPage();
      } else {
        console.error('外部 API 页面未加载');
      }
    });
  }
});