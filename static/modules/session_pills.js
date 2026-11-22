// static/modules/session_pills.js
// 会话快捷胶囊：后台任务 / 子智能体 / 权限；复用 param-pill，不新建页面
(function () {
  const CSS = `
  .sp-panel{position:fixed;z-index:12000;width:320px;max-height:420px;overflow:auto;background:#fff;
    border:1px solid #e5e5e5;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.16);padding:10px;font-size:13px}
  .sp-title{font-weight:600;margin:2px 0 8px;color:#333}
  .sp-empty{color:#999;padding:12px;text-align:center}
  .sp-row{display:flex;align-items:center;gap:8px;padding:8px 6px;border-bottom:1px solid #f1f1f1}
  .sp-row:last-child{border-bottom:none}
  .sp-main{flex:1;min-width:0}
  .sp-name{font-weight:500;color:#333;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .sp-sub{color:#999;font-size:11px;margin-top:2px}
  .sp-btn{border:1px solid #007aff;background:#fff;color:#007aff;border-radius:7px;padding:3px 9px;cursor:pointer;font-size:12px}
  .sp-btn.warn{border-color:#ff9500;color:#ff9500}
  .sp-perm{display:flex;align-items:center;justify-content:space-between;padding:10px 6px;border-bottom:1px solid #f1f1f1}
  .sp-perm label{cursor:pointer}
  `;
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);

  let panel = null;
  let currentType = '';
  let timer = null;

  function token() { return localStorage.getItem('sases_token') || ''; }
  async function api(path, opts) {
    const o = Object.assign({ headers: { 'Authorization': 'Bearer ' + token() } }, opts || {});
    if (o.body) o.headers['Content-Type'] = 'application/json';
    const r = await fetch(path, o);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }

  function ensurePills() {
    const bar = document.getElementById('param-bar');
    if (!bar) return;
    const apiPill = document.getElementById('api-pill');
    if (!apiPill) return;
    let anchor = apiPill;
    [['task-pill', '⏳ 后台'], ['agent-pill', '🤖 子智能体'], ['perm-pill', '🔐 权限']].forEach(function (p) {
      if (document.getElementById(p[0])) {
        anchor = document.getElementById(p[0]);
        return;
      }
      const el = document.createElement('div');
      el.id = p[0];
      el.className = 'param-pill';
      el.textContent = p[1];
      el.style.cursor = 'pointer';
      el.onclick = function (e) { e.stopPropagation(); toggle(p[0]); };
      anchor.parentNode.insertBefore(el, anchor.nextSibling);
      anchor = el;
    });
  }

  function close() {
    if (panel) panel.remove();
    panel = null;
    currentType = '';
    if (timer) { clearInterval(timer); timer = null; }
  }

  function toggle(type) {
    if (currentType === type) { close(); return; }
    close();
    currentType = type;
    panel = document.createElement('div');
    panel.className = 'sp-panel';
    const pill = document.getElementById(type);
    const r = pill.getBoundingClientRect();
    panel.style.left = Math.max(8, Math.min(r.left, innerWidth - 336)) + 'px';
    // 和能力胶囊一致：面板在按钮上方展开，避免遮住输入框
    panel.style.top = 'auto';
    panel.style.bottom = Math.max(8, innerHeight - r.top + 6) + 'px';
    panel.onclick = function (e) { e.stopPropagation(); };
    document.body.appendChild(panel);
    render();
    if (type === 'task-pill') timer = setInterval(render, 5000);
  }

  async function render() {
    if (!panel) return;
    if (currentType === 'task-pill') return renderTasks();
    if (currentType === 'agent-pill') return renderAgents();
    if (currentType === 'perm-pill') return renderPerms();
  }

  async function renderTasks() {
    panel.innerHTML = '<div class="sp-title">后台任务</div><div class="sp-empty">加载中...</div>';
    try {
      const data = await api('/supervisor/runs');
      const runs = data.runs || [];
      if (!runs.length) { panel.innerHTML = '<div class="sp-title">后台任务</div><div class="sp-empty">暂无运行中的任务</div>'; return; }
      panel.innerHTML = '<div class="sp-title">后台任务</div>' + runs.map(function (r) {
        const paused = r.status === 'paused';
        return '<div class="sp-row"><div class="sp-main"><div class="sp-name">' + esc(r.goal || ('run #' + r.id)) +
          '</div><div class="sp-sub">run #' + r.id + ' · ' + esc(r.status) + '</div></div>' +
          '<button class="sp-btn ' + (paused ? 'warn' : '') + '" data-run="' + r.id + '" data-paused="' + (paused ? '1' : '0') + '">' +
          (paused ? '继续' : '暂停') + '</button></div>';
      }).join('');
      panel.querySelectorAll('[data-run]').forEach(function (b) {
        b.onclick = async function () {
          const id = b.getAttribute('data-run');
          const paused = b.getAttribute('data-paused') === '1';
          b.disabled = true;
          try { await api('/supervisor/runs/' + id + (paused ? '/resume' : '/pause'), { method: 'POST' }); await render(); }
          catch (e) { b.textContent = '失败'; b.disabled = false; }
        };
      });
    } catch (e) { panel.innerHTML = '<div class="sp-title">后台任务</div><div class="sp-empty">加载失败</div>'; }
  }

  async function renderAgents() {
    panel.innerHTML = '<div class="sp-title">子智能体</div><div class="sp-empty">加载中...</div>';
    try {
      const data = await api('/agents/list');
      const list = data.agents || [];
      if (!list.length) { panel.innerHTML = '<div class="sp-title">子智能体</div><div class="sp-empty">暂无智能体，请到模型管理添加</div>'; return; }
      panel.innerHTML = '<div class="sp-title">子智能体 <span style="font-weight:400;color:#999;font-size:11px">与模型管理同步</span></div>' +
        list.map(function (a) {
          return '<div class="sp-row"><div class="sp-main"><div class="sp-name">' + esc(a.name || a.agent_id) +
            '</div><div class="sp-sub">' + esc(a.type || '') + ' · ' + esc(a.agent_id || '') + '</div></div></div>';
        }).join('');
    } catch (e) { panel.innerHTML = '<div class="sp-title">子智能体</div><div class="sp-empty">加载失败</div>'; }
  }

  function renderPerms() {
    let p = { web: false, write: false, schedule: true };
    try { p = Object.assign(p, JSON.parse(localStorage.getItem('sases_perms_v1') || '{}')); } catch (e) {}
    const row = (k, label, desc) => '<div class="sp-perm"><div><div class="sp-name">' + label +
      '</div><div class="sp-sub">' + desc + '</div></div><input type="checkbox" data-perm="' + k + '" ' + (p[k] ? 'checked' : '') + '></div>';
    panel.innerHTML = '<div class="sp-title">权限</div>' +
      row('web', '联网', '允许读取网页 / 外部 API') +
      row('write', '写文件', '允许修改项目文件') +
      row('schedule', '定时', '允许创建定时任务');
    panel.querySelectorAll('[data-perm]').forEach(function (el) {
      el.onchange = function () {
        p[el.getAttribute('data-perm')] = el.checked;
        localStorage.setItem('sases_perms_v1', JSON.stringify(p));
      };
    });
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function bindInput() {
    const input = document.getElementById('chat-input');
    if (!input || input._spBound) return;
    input._spBound = true;
    const resize = function () {
      input.style.height = 'auto';
      const h = Math.min(input.scrollHeight, 160);
      input.style.height = h + 'px';
      input.style.overflowY = input.scrollHeight > 160 ? 'auto' : 'hidden';
    };
    input.addEventListener('input', resize);
    input.addEventListener('focus', resize);
    const send = document.getElementById('send-btn');
    if (send) send.addEventListener('click', function () { setTimeout(resize, 0); });
    resize();
  }

  function boot() {
    ensurePills();
    bindInput();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  document.addEventListener('click', function () { if (currentType) close(); });
  new MutationObserver(boot).observe(document.body, { childList: true, subtree: true });
})();
