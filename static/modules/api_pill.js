// static/modules/api_pill.js
// 胶囊面板：外部 API / 工具 / 技能，按权限域分组；右侧 ⋯ 可设置显示哪些组
(function () {
  var STORE = 'sases_capsules_v1';
  var PERM_KEY = 'sases_perms_v1';
  var state = { apis: [], tools: [], skills: [], hidden: [] };
  var groups = [];
  var perms = { web: false, write: false, schedule: true };

  function loadPerms() {
    try {
      var raw = localStorage.getItem(PERM_KEY);
      if (!raw) return;
      var p = JSON.parse(raw);
      perms.web = !!p.web;
      perms.write = !!p.write;
      perms.schedule = p.schedule !== false;
    } catch (e) {}
  }

  function savePerms() {
    try { localStorage.setItem(PERM_KEY, JSON.stringify(perms)); } catch (e) {}
  }

  function permsHtml() {
    var rows = [
      ['web', '联网', '允许读取网页 / 调用外部 API'],
      ['write', '改文件', '允许修改项目文件（需确认）'],
      ['schedule', '定时', '允许创建定时任务']
    ];
    var h = '<div class="cp-perms"><div class="cp-ptitle">能力开关</div>';
    rows.forEach(function (r) {
      h += '<label class="cp-perm"><input type="checkbox" data-perm="' + r[0] + '" ' +
        (perms[r[0]] ? 'checked' : '') + '><span>' + r[1] + '</span>' +
        '<span class="cp-pdesc">' + r[2] + '</span></label>';
    });
    return h + '</div>';
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORE);
      if (raw) {
        var s = JSON.parse(raw);
        state.apis = s.apis || [];
        state.tools = [];
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
    // 工具由系统按任务自动选择，不再由胶囊勾选限制
    window.currentSessionTools = null;
    window.currentSessionSkills = state.skills.slice();
  }

  function total() { return state.apis.length + state.skills.length; }

  function updatePill() {
    var p = document.getElementById('api-pill');
    if (!p) return;
    p.textContent = '🧩 能力';
    renderChips();
  }

  function _findLabel(id) {
    for (var i = 0; i < groups.length; i++) {
      var its = groups[i].items || [];
      for (var j = 0; j < its.length; j++) if (its[j].id === id) return its[j].label;
    }
    return id;
  }

  function renderChips() {
    var bar = document.getElementById('param-bar');
    if (!bar) return;
    bar.querySelectorAll('.param-chip').forEach(function (x) { x.remove(); });
    var items = [];
    state.apis.forEach(function (id) { items.push({ id: id, type: 'api' }); });
    state.skills.forEach(function (id) { items.push({ id: id, type: 'skill' }); });
    var settings = document.getElementById('capsule-settings-btn');
    items.forEach(function (it) {
      var chip = document.createElement('span');
      chip.className = 'param-pill param-chip';
      chip.textContent = _findLabel(it.id) + ' ×';
      chip.title = '点击移除';
      chip.onclick = function () {
        if (it.type === 'api') state.apis = state.apis.filter(function (x) { return x !== it.id; });
        else state.skills = state.skills.filter(function (x) { return x !== it.id; });
        save();
      };
      if (settings) bar.insertBefore(chip, settings);
      else bar.appendChild(chip);
    });
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
      '#capsule-panel .cp-perms{padding:8px 10px;border-bottom:1px solid #eee;background:#fbfcff}',
      '#capsule-panel .cp-ptitle{font-size:11px;color:#888;margin-bottom:4px}',
      '#capsule-panel .cp-perm{display:flex;align-items:center;gap:6px;padding:3px 0;font-size:12px;cursor:pointer}',
      '#capsule-panel .cp-pdesc{color:#aaa;font-size:10px;margin-left:auto}',
      '#capsule-panel .cp-tab{flex:1;text-align:center;padding:8px 0;cursor:pointer;color:#666}',
      '#capsule-panel .cp-tab.active{color:#007aff;font-weight:600;box-shadow:inset 0 -2px 0 #007aff}',
      '#capsule-panel .cp-body{flex:1;overflow-y:auto;padding:6px 8px}',
      '#capsule-panel .cp-search{padding:6px 8px;border-bottom:1px solid #eee}',
      '#capsule-panel .cp-search input{width:100%;box-sizing:border-box;padding:6px 8px;border:1px solid #ddd;border-radius:7px;font-size:12px}',
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
      '#capsule-settings-menu{position:fixed;width:260px;background:#fff;border:1px solid #e5e5e5;border-radius:10px;',
      'box-shadow:0 8px 24px rgba(0,0,0,.14);z-index:9999;display:none;padding:6px;font-size:12px;font-family:system-ui}',
      '#capsule-settings-menu.show{display:block}',
      '#capsule-settings-menu .sm-title{padding:6px 6px 2px;color:#999;font-size:11px}',
      '#capsule-settings-menu .sm-item{display:flex;align-items:center;gap:8px;padding:5px 6px;border-radius:6px;cursor:pointer}',
      '#capsule-settings-menu .sm-select{margin-left:auto;border:1px solid #ddd;border-radius:5px;padding:2px 4px;font-size:12px}',
      '#capsule-settings-menu .sm-item{display:flex;align-items:center;gap:8px;padding:5px 6px;border-radius:6px;cursor:pointer}',
      '#capsule-settings-menu .sm-item:hover{background:#f6f8fb}',
      '#capsule-settings-menu .sm-reset{color:#d93025;text-align:center;padding:6px;cursor:pointer;border-top:1px solid #eee;margin-top:4px}'
    ].join('');
    document.head.appendChild(s);
  }

  var _tab = 'api';
  var _skillQuery = '';
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
      ['api', '外部 API'], ['skill', '技能']
    ];
    var html = '<div class="cp-tabs">';
    tabs.forEach(function (t) {
      html += '<div class="cp-tab ' + (_tab === t[0] ? 'active' : '') + '" data-tab="' + t[0] + '">' + t[1] + '</div>';
    });
    html += '</div>';
    if (_tab === 'skill') {
      html += '<div class="cp-search"><input id="cp-skill-search" placeholder="搜索 DSH 技能，如 doc / office / verify" value="' +
        String(_skillQuery).replace(/"/g, '&quot;') + '"></div>';
    }
    html += '<div class="cp-body">';

    var shown = groups.filter(function (g) {
      return _tab === 'api' ? g.id === 'external' : g.id === 'skill';
    });

    if (!shown.length) {
      html += '<div class="cp-empty">' + (_tab === 'skill'
        ? '暂无技能<br><span style="font-size:11px;color:#aaa">放入 data/skills/&lt;名称&gt;/SKILL.md<br><a href="/static/skills_help.html" target="_blank">格式说明</a></span>'
        : '暂无外部 API') + '</div>';
    }
    shown.forEach(function (g) {
      var items = (g.items || []).filter(function (it) {
        if (_tab !== 'skill' || !_skillQuery) return true;
        return (String(it.label) + ' ' + String(it.desc || '')).toLowerCase().indexOf(_skillQuery.toLowerCase()) !== -1;
      });
      html += '<div class="cp-group"><div class="cp-ghead">' + g.label +
        '<span class="cp-risk ' + (g.risk || '') + '">' +
        (g.risk === 'write' ? '写' : (g.risk === 'network' ? '网络' : '读')) + '</span></div>';
      items.forEach(function (it) {
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
    var _si = document.getElementById('cp-skill-search');
    if (_si) _si.onchange = function () { _skillQuery = _si.value || ''; render(); };
    _panel.querySelectorAll('.cp-perm input').forEach(function (el) {
      el.onchange = function () {
        perms[el.dataset.perm] = el.checked;
        savePerms();
      };
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
        if (!groups.some(function (g) { return g.id === 'external'; })) _tab = 'api';
        load();
        render();
        renderChips();
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
    var _steps = localStorage.getItem('sases_max_steps') || '8';
    var _mode = localStorage.getItem('sases_agent_mode') || 'auto';
    var _exec = localStorage.getItem('sases_exec_mode') || 'single';
    var _font = localStorage.getItem('sases_chat_font') || '15';
    var html = '<div class="sm-title">高级</div>';
    html += '<label class="sm-item">轮数<select class="sm-select" id="sm-rounds">' +
      ['5', '8', '15', '-1'].map(function (v) {
        return '<option value="' + v + '" ' + (String(_steps) === v ? 'selected' : '') + '>' + (v === '-1' ? '不限' : v + '步') + '</option>';
      }).join('') + '</select></label>';
    html += '<label class="sm-item">模式<select class="sm-select" id="sm-mode">' +
      [['auto', '自动'], ['fast', '快速'], ['strict', '严格']].map(function (v) {
        return '<option value="' + v[0] + '" ' + (_mode === v[0] ? 'selected' : '') + '>' + v[1] + '</option>';
      }).join('') + '</select></label>';
    html += '<label class="sm-item">字体<select class="sm-select" id="sm-font">' +
      [['14', '小'], ['15', '中'], ['17', '大']].map(function (v) {
        return '<option value="' + v[0] + '" ' + (_font === v[0] ? 'selected' : '') + '>' + v[1] + '</option>';
      }).join('') + '</select></label>';
    html += '<div class="sm-title">显示</div>';
    html += '<div class="sm-item" style="color:#999">工具由系统按任务自动选择</div>';
    html += '<div class="sm-reset" id="sm-reset">恢复默认</div>';
    html += '<label class="sm-item">执行<select class="sm-select" id="sm-exec">' +
      [['single', '单窗口'], ['background', '后台执行'], ['multi', '多子智能体']].map(function (v) {
        return '<option value="' + v[0] + '" ' + (_exec === v[0] ? 'selected' : '') + '>' + v[1] + '</option>';
      }).join('') + '</select></label>';
    html += '<div class="sm-item" id="sm-capacity" style="color:#999;font-size:12px;">并发：读取中…</div>';
    m.innerHTML = html;
    try {
      fetch('/system/capacity', { headers: { Authorization: 'Bearer ' + token() } })
        .then(function (r) { return r.json(); })
        .then(function (c) {
          var el = document.getElementById('sm-capacity');
          if (el) el.textContent = '并发：读 ' + (c.read_parallel || 1) +
            ' / 写 ' + (c.write_parallel || 1) + ' / 后台 ' + (c.background_parallel || 1);
        })
        .catch(function () {});
    } catch (e) {}

    var _rounds = document.getElementById('sm-rounds');
    if (_rounds) _rounds.onchange = function () {
      var v = parseInt(_rounds.value, 10);
      try {
        if (window.sasesParamBar && window.sasesParamBar.setParamMaxSteps) window.sasesParamBar.setParamMaxSteps(v);
        else localStorage.setItem('sases_max_steps', String(v));
      } catch (e) {}
    };
    var _modeSel = document.getElementById('sm-mode');
    if (_modeSel) _modeSel.onchange = function () {
      try {
        if (window.sasesParamBar && window.sasesParamBar.setAgentMode) window.sasesParamBar.setAgentMode(_modeSel.value);
        else localStorage.setItem('sases_agent_mode', _modeSel.value);
      } catch (e) {}
    };
    var _fontSel = document.getElementById('sm-font');
    var _execSel = document.getElementById('sm-exec');
    if (_execSel) _execSel.onchange = function () {
      try { localStorage.setItem('sases_exec_mode', _execSel.value); } catch (e) {}
    };
    if (_fontSel) _fontSel.onchange = function () {
      try {
        localStorage.setItem('sases_chat_font', _fontSel.value);
        document.documentElement.style.setProperty('--chat-font-size', _fontSel.value + 'px');
        document.documentElement.style.setProperty('--chat-line-height',
          _fontSel.value === '14' ? '1.6' : (_fontSel.value === '17' ? '1.7' : '1.65'));
      } catch (e) {}
    };
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
      try {
        localStorage.removeItem('sases_max_steps');
        localStorage.removeItem('sases_agent_mode');
      } catch (e) {}
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
    try {
      var _f = localStorage.getItem('sases_chat_font') || '15';
      document.documentElement.style.setProperty('--chat-font-size', _f + 'px');
      document.documentElement.style.setProperty('--chat-line-height',
        _f === '14' ? '1.6' : (_f === '17' ? '1.7' : '1.65'));
    } catch (e) {}
    loadPerms();
    load();
    syncGlobals();
    updatePill();
    fetch('/tools/capsules', { headers: { Authorization: 'Bearer ' + token() } })
      .then(function (res) { return res.json(); })
      .then(function (data) { groups = data.groups || []; renderChips(); })
      .catch(function () {});

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
