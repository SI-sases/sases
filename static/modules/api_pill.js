// static/modules/api_pill.js
// 胶囊面板：外部 API / 工具 / 技能，按权限域分组；右侧 ⋯ 可设置显示哪些组
(function () {
  var STORE = 'sases_capsules_v1';
  var state = { apis: [], tools: [], skills: [], hidden: [] };
  var groups = [];

  function load() {
    try {
      var raw = localStorage.getItem(STORE);
      if (raw) {
        var s = JSON.parse(raw);
        state.apis = s.apis || [];
        state.tools = s.tools || [];
        state.skills = s.skills || [];
        state.hidden = s.hidden || [];
        return true;
      }
    } catch (e) {}
    return false;
  }

  function save() {
    try { localStorage.setItem(STORE, JSON.stringify(state)); } catch (e) {}
    syncGlobals();
    updatePill();
  }

  function syncGlobals() {
    window.currentSessionAPIs = state.apis.slice();
    window.currentSessionTools = state.tools.slice();
    window.currentSessionSkills = state.skills.slice();
  }

  function total() { return state.apis.length + state.tools.length + state.skills.length; }

  function updatePill() {
    var p = document.getElementById('api-pill');
    if (!p) return;
    p.textContent = total() > 0 ? ('🧩 能力 (' + total() + ')') : '🧩 能力';
  }

  function token() { return localStorage.getItem('sases_token') || ''; }

  function css() {
    if (document.getElementById('capsule-style')) return;
    var s = document.createElement('style');
    s.id = 'capsule-style';
    s.textContent = [
      '#capsule-panel{position:fixed;width:320px;max-height:420px;background:#fff;border:1px solid #e5e5e5;',
      'border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.14);z-index:9999;display:none;flex-direction:column;overflow:hidden;',
      'font-family:system-ui,-apple-system,sans-serif;font-size:13px}',
      '#capsule-panel.show{display:flex}',
      '#capsule-panel .cp-tabs{display:flex;border-bottom:1px solid #eee;background:#fafafa}',
      '#capsule-panel .cp-tab{flex:1;text-align:center;padding:8px 0;cursor:pointer;color:#666}',
      '#capsule-panel .cp-tab.active{color:#007aff;font-weight:600;box-shadow:inset 0 -2px 0 #007aff}',
      '#capsule-panel .cp-body{flex:1;overflow-y:auto;padding:6px 8px}',
      '#capsule-panel .cp-group{margin-bottom:8px}',
      '#capsule-panel .cp-ghead{display:flex;align-items:center;gap:6px;padding:4px 2px;color:#333;font-weight:600;font-size:12px}',
      '#capsule-panel .cp-risk{margin-left:auto;font-size:10px;padding:1px 5px;border-radius:7px;background:#eef4ff;color:#1a73e8}',
      '#capsule-panel .cp-risk.write{background:#fff4e5;color:#b26a00}',
      '#capsule-panel .cp-risk.network{background:#eef7ee;color:#2e7d32}',
      '#capsule-panel .cp-item{display:flex;align-items:flex-start;gap:8px;padding:5px 4px;border-radius:6px;cursor:pointer}',
      '#capsule-panel .cp-item:hover{background:#f7f9fc}',
      '#capsule-panel .cp-item input{margin-top:2px}',
      '#capsule-panel .cp-name{font-size:12px;color:#222}',
      '#capsule-panel .cp-desc{font-size:10px;color:#999;margin-top:1px;word-break:break-all}',
      '#capsule-panel .cp-empty{color:#999;text-align:center;padding:20px}',
      '#capsule-panel .cp-foot{border-top:1px solid #eee;padding:6px 10px;display:flex;align-items:center;gap:8px;color:#888;font-size:11px}',
      '#capsule-settings-menu{position:fixed;width:220px;background:#fff;border:1px solid #e5e5e5;border-radius:10px;',
      'box-shadow:0 8px 24px rgba(0,0,0,.14);z-index:9999;display:none;padding:6px;font-size:12px;font-family:system-ui}',
      '#capsule-settings-menu.show{display:block}',
      '#capsule-settings-menu .sm-item{display:flex;align-items:center;gap:8px;padding:5px 6px;border-radius:6px;cursor:pointer}',
      '#capsule-settings-menu .sm-item:hover{background:#f6f8fb}',
      '#capsule-settings-menu .sm-reset{color:#d93025;text-align:center;padding:6px;cursor:pointer;border-top:1px solid #eee;margin-top:4px}'
    ].join('');
    document.head.appendChild(s);
  }

  var _tab = 'api';
  var _panel = null;

  function inState(type) {
    if (type === 'api') return state.apis;
    if (type === 'tool') return state.tools;
    return state.skills;
  }

  function toggle(item, on) {
    var arr = inState(item.type);
    var i = arr.indexOf(item.id);
    if (on && i === -1) arr.push(item.id);
    if (!on && i !== -1) arr.splice(i, 1);
    save();
  }

  function render() {
    if (!_panel) return;
    var tabs = [
      ['api', '外部 API'], ['tool', '工具'], ['skill', '技能']
    ];
    var html = '<div class="cp-tabs">';
    tabs.forEach(function (t) {
      html += '<div class="cp-tab ' + (_tab === t[0] ? 'active' : '') + '" data-tab="' + t[0] + '">' + t[1] + '</div>';
    });
    html += '</div><div class="cp-body">';

    var shown = groups.filter(function (g) {
      if (state.hidden.indexOf(g.id) !== -1) return false;
      if (_tab === 'api') return g.id === 'external';
      if (_tab === 'tool') return g.id !== 'external' && g.id !== 'skill';
      return g.id === 'skill';
    });

    if (!shown.length) {
      html += '<div class="cp-empty">' + (_tab === 'skill' ? '暂无技能（data/skills/*.md）' : '暂无可选项') + '</div>';
    }
    shown.forEach(function (g) {
      html += '<div class="cp-group"><div class="cp-ghead">' + g.label +
        '<span class="cp-risk ' + (g.risk || '') + '">' +
        (g.risk === 'write' ? '写' : (g.risk === 'network' ? '网络' : '读')) + '</span></div>';
      g.items.forEach(function (it) {
        var checked = inState(it.type).indexOf(it.id) !== -1 ? 'checked' : '';
        html += '<label class="cp-item"><input type="checkbox" ' + checked +
          ' data-type="' + it.type + '" data-id="' + it.id + '">' +
          '<div><div class="cp-name">' + it.label + '</div><div class="cp-desc">' + (it.desc || '') + '</div></div></label>';
      });
      html += '</div>';
    });
    html += '</div><div class="cp-foot"><span>已选 ' + total() + ' 项</span>' +
      '<span style="margin-left:auto;cursor:pointer" id="cp-clear">清空</span></div>';
    _panel.innerHTML = html;

    _panel.querySelectorAll('.cp-tab').forEach(function (el) {
      el.onclick = function () { _tab = el.dataset.tab; render(); };
    });
    _panel.querySelectorAll('.cp-item input').forEach(function (el) {
      el.onchange = function () {
        toggle({ type: el.dataset.type, id: el.dataset.id }, el.checked);
        render();
      };
    });
    var clear = document.getElementById('cp-clear');
    if (clear) clear.onclick = function () { state.apis = []; state.tools = []; state.skills = []; save(); render(); };
  }

  function togglePanel() {
    css();
    if (!_panel) {
      _panel = document.createElement('div');
      _panel.id = 'capsule-panel';
      document.body.appendChild(_panel);
    }
    if (_panel.classList.contains('show')) { _panel.classList.remove('show'); return; }
    var pill = document.getElementById('api-pill');
    var r = pill.getBoundingClientRect();
    _panel.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 330)) + 'px';
    _panel.style.bottom = (window.innerHeight - r.top + 6) + 'px';
    _panel.classList.add('show');
    _panel.innerHTML = '<div class="cp-empty">加载中...</div>';
    fetch('/tools/capsules', { headers: { Authorization: 'Bearer ' + token() } })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        groups = data.groups || [];
        if (!groups.some(function (g) { return g.id === 'external'; })) _tab = 'tool';
        if (!load()) {
          groups.forEach(function (g) {
            if (g.default_on) g.items.forEach(function (it) { inState(it.type).push(it.id); });
          });
          save();
        }
        render();
      })
      .catch(function (e) {
        _panel.innerHTML = '<div class="cp-empty">加载失败：' + e.message + '</div>';
      });
  }

  function toggleSettings() {
    css();
    var m = document.getElementById('capsule-settings-menu');
    if (!m) {
      m = document.createElement('div');
      m.id = 'capsule-settings-menu';
      document.body.appendChild(m);
    }
    if (m.classList.contains('show')) { m.classList.remove('show'); return; }
    var all = [['read', '读取'], ['write', '写入'], ['network', '网络'], ['git', 'Git'], ['external', '外部 API'], ['skill', '技能']];
    var html = '<div style="padding:4px 6px;color:#999">显示哪些胶囊组</div>';
    all.forEach(function (a) {
      var hidden = state.hidden.indexOf(a[0]) !== -1;
      html += '<label class="sm-item"><input type="checkbox" data-g="' + a[0] + '" ' + (hidden ? '' : 'checked') + '>' + a[1] + '</label>';
    });
    html += '<div class="sm-reset" id="sm-reset">恢复默认</div>';
    m.innerHTML = html;
    m.querySelectorAll('input').forEach(function (el) {
      el.onchange = function () {
        var g = el.dataset.g;
        var i = state.hidden.indexOf(g);
        if (!el.checked && i === -1) state.hidden.push(g);
        if (el.checked && i !== -1) state.hidden.splice(i, 1);
        save();
      };
    });
    var reset = document.getElementById('sm-reset');
    if (reset) reset.onclick = function () {
      state.apis = []; state.tools = []; state.skills = []; state.hidden = [];
      save();
      m.classList.remove('show');
    };
    var btn = document.getElementById('capsule-settings-btn');
    var r = btn.getBoundingClientRect();
    m.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 230)) + 'px';
    m.style.bottom = (window.innerHeight - r.top + 6) + 'px';
    m.classList.add('show');
  }

  document.addEventListener('DOMContentLoaded', function () {
    css();
    load();
    syncGlobals();
    updatePill();

    var pill = document.getElementById('api-pill');
    if (pill) pill.onclick = function (e) { e.stopPropagation(); togglePanel(); };

    var settings = document.getElementById('capsule-settings-btn');
    if (settings) settings.onclick = function (e) { e.stopPropagation(); toggleSettings(); };

    document.addEventListener('click', function (e) {
      var p = document.getElementById('capsule-panel');
      if (p && !p.contains(e.target) && e.target.id !== 'api-pill') p.classList.remove('show');
      var m = document.getElementById('capsule-settings-menu');
      if (m && !m.contains(e.target) && e.target.id !== 'capsule-settings-btn') m.classList.remove('show');
    });
  });
})();
