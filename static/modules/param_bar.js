// 参数胶囊栏（v0.37.0）
// 用法：initParamBar() 初始化；getParamMaxSteps() 读取当前值

const STORAGE_KEY = 'sases_max_steps';
const DEFAULT_STEPS = 8;

const PRESETS = [
  { value: 5, label: '5步', desc: '快速任务' },
  { value: 8, label: '8步', desc: '默认' },
  { value: 15, label: '15步', desc: '复杂任务' },
  { value: -1, label: '不限', desc: '谨慎使用' },
];

let _currentValue = null;

function _read() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === null) return DEFAULT_STEPS;
  const v = parseInt(raw, 10);
  if (isNaN(v)) return DEFAULT_STEPS;
  return v;
}

function _write(v) {
  localStorage.setItem(STORAGE_KEY, String(v));
  _currentValue = v;
}

function _labelOf(v) {
  if (v === -1) return '不限';
  return v + '步';
}

function _updatePill() {
  const pill = document.getElementById('param-rounds');
  if (!pill) return;
  const v = getParamMaxSteps();
  pill.textContent = '⚙️ ' + _labelOf(v);
  pill.classList.remove('param-modified', 'param-unlimited');
  if (v === -1) {
    pill.classList.add('param-unlimited');
  } else if (v !== DEFAULT_STEPS) {
    pill.classList.add('param-modified');
  }
}

function _ensureMenu() {
  let menu = document.getElementById('param-menu');
  if (menu) return menu;
  menu = document.createElement('div');
  menu.id = 'param-menu';
  menu.className = 'param-menu';
  document.body.appendChild(menu);
  return menu;
}

function _renderMenu(menu, onPick) {
  menu.innerHTML = '';
  PRESETS.forEach(p => {
    const item = document.createElement('div');
    item.className = 'param-menu-item' + (p.value === _currentValue ? ' active' : '');
    item.innerHTML = p.label + '<span class="param-desc">' + p.desc + '</span>';
    item.onclick = () => {
      onPick(p.value);
      _hideMenu();
    };
    menu.appendChild(item);
  });
}

function _showMenu(anchorEl) {
  const menu = _ensureMenu();
  _renderMenu(menu, (v) => {
    _write(v);
    _updatePill();
  });
  const rect = anchorEl.getBoundingClientRect();
  menu.style.left = rect.left + 'px';
  menu.style.bottom = (window.innerHeight - rect.top + 6) + 'px';
  menu.classList.add('show');
}

function _hideMenu() {
  const menu = document.getElementById('param-menu');
  if (menu) menu.classList.remove('show');
}


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
            html += '<label style="display:flex; align-items:center; padding:8px 12px; cursor:pointer;"><input type="checkbox" ' + checked + ' onchange="window.__toggleApi(\'ext_api_' + a.id + '\')" style="margin-right:8px;"><div><div style="font-size:14px;">' + a.api_name + '</div><div style="font-size:11px; color:#999;">' + a.method + ' ' + a.endpoint + '</div></div></label>';
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

export function initParamBar() {
  if (typeof window.initApiPill === "function") window.initApiPill();
  window.initApiPill();
  _currentValue = _read();
  const pill = document.getElementById('param-rounds');
  if (!pill) return;
  _updatePill();
  if (!pill._sasesParamBound) {
    pill._sasesParamBound = true;
    pill.onclick = (e) => {
      e.stopPropagation();
      const menu = document.getElementById('param-menu');
      if (menu && menu.classList.contains('show')) {
        _hideMenu();
      } else {
        _showMenu(pill);
      }
    };
  }
  if (!window._sasesParamGlobalBound) {
    window._sasesParamGlobalBound = true;
    document.addEventListener('click', () => _hideMenu());
  }
}

export function getParamMaxSteps() {
  if (_currentValue === null) _currentValue = _read();
  return _currentValue;
}

export function setParamMaxSteps(v) {
  _write(v);
  _updatePill();
}

// 挂到 window 供 chat.js 非模块化调用
if (typeof window !== 'undefined') {
  window.sasesParamBar = { initParamBar, getParamMaxSteps, setParamMaxSteps };
}