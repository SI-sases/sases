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
    panel.addEventListener('click', function (e) {
      if (e.target && e.target.closest && e.target.closest('button')) return;
      const row = e.target && e.target.closest ? e.target.closest('.sp-row') : null;
      if (!row) return;
      const d = row.querySelector('.sp-detail');
      if (d) d.style.display = d.style.display === 'none' ? 'block' : 'none';
    });
    document.body.appendChild(panel);
    render();
    if (type === 'task-pill') timer = setInterval(render, 2000);
  }

  async function render() {
    if (!panel) return;
    if (currentType === 'task-pill') return renderTasks();
    if (currentType === 'agent-pill') return renderAgents();
    if (currentType === 'perm-pill') return renderPerms();
  }

  async function renderTasks() {
    panel.innerHTML = '<div class="sp-title">' + t('sp_tasks') + '</div><div class="sp-empty">' + t('sp_loading') + '</div>';
    try {
      const data = await api('/supervisor/runs');
      const runs = data.runs || [];
      if (!runs.length) { panel.innerHTML = '<div class="sp-title">' + t('sp_tasks') + '</div><div class="sp-empty">' + t('sp_no_tasks') + '</div>'; return; }
      panel.innerHTML = '<div class="sp-title">' + t('sp_tasks') +
        (runs.filter(function (x) { return x.status === 'queued'; }).length ? ' · ' + t('sp_queued') + ' ' +
          runs.filter(function (x) { return x.status === 'queued'; }).length : '') + '</div>' + runs.map(function (r) {
        const paused = r.status === 'paused' || r.status === 'partial';
        const child = r.parent_run_id ? ' sp-child' : '';
        const label = r.parent_run_id ? '↳ ' : '';
        return '<div class="sp-row' + child + '"><div class="sp-main"><div class="sp-name">' + label + esc(r.goal || ('run #' + r.id)) +
          '</div><div class="sp-sub">run #' + r.id + ' · ' + esc(r.status) + '</div>' +
          (r.last_result ? '<div class="sp-detail" style="display:none;white-space:pre-wrap;margin-top:6px;font-size:11px;color:#555;max-height:160px;overflow:auto;">' +
            esc(String(r.last_result).slice(0, 1200)) + '</div>' : '') +
          '</div>' +
          (r.parent_run_id ? (r.status === 'failed' ? (Number(r.retry_count || 0) >= 3 ?
            '<span class="sp-sub">' + t('sp_retry_limit') + '</span>' : '<button class="sp-btn warn" data-retry="' + r.id + '">' + t('sp_retry') + '</button>') : '') :
            '<button class="sp-btn ' + (paused ? 'warn' : '') + '" data-run="' + r.id + '" data-paused="' + (paused ? '1' : '0') + '">' +
            (paused ? t('sp_resume') : t('sp_pause')) + '</button><button class="sp-btn" data-cancel="' + r.id + '" style="margin-left:4px;">' + t('sp_cancel') + '</button>') + '</div>';
      }).join('');
      panel.querySelectorAll('[data-cancel]').forEach(function (b) {
        b.onclick = async function (ev) {
          ev.stopPropagation();
          const id = b.getAttribute('data-cancel');
          b.disabled = true;
          b.textContent = t('sp_canceling');
          try { await api('/supervisor/runs/' + id + '/cancel', { method: 'POST' }); await render(); }
          catch (e) { b.textContent = t('sp_failed'); b.disabled = false; }
        };
      });
      panel.querySelectorAll('[data-retry]').forEach(function (b) {
        b.onclick = async function (ev) {
          ev.stopPropagation();
          const id = b.getAttribute('data-retry');
          b.disabled = true;
          b.textContent = t('sp_retrying');
          try { await api('/supervisor/runs/' + id + '/resume', { method: 'POST' }); await render(); }
          catch (e) { b.textContent = t('sp_failed'); b.disabled = false; }
        };
      });
      panel.querySelectorAll('[data-run]').forEach(function (b) {
        b.onclick = async function () {
          const id = b.getAttribute('data-run');
          const paused = b.getAttribute('data-paused') === '1';
          const action = paused ? 'resume' : 'pause';
          b.disabled = true;
          b.textContent = paused ? t('sp_resuming') : t('sp_pausing');
          try {
            // 真实调用后端接口：POST /supervisor/runs/{id}/pause|resume
            const res = await api('/supervisor/runs/' + id + '/' + action, { method: 'POST' });
            if (res && res.ok === false) throw new Error('接口返回失败');
            if (action === 'resume' && res && res.resumed === false) {
              b.textContent = t('sp_unpaused');
            }
            await render();
          } catch (e) {
            b.textContent = t('sp_failed');
            b.disabled = false;
            b.setAttribute('data-error', '1');
            console.warn('[task-pill] ' + action + ' 失败 run#' + id, e);
          }
        };
      });
    } catch (e) { panel.innerHTML = '<div class="sp-title">' + t('sp_tasks') + '</div><div class="sp-empty">' + t('sp_load_failed') + '</div>'; }
  }

  async function renderAgents() {
    panel.innerHTML = '<div class="sp-title">' + t('sp_agents') + '</div><div class="sp-empty">' + t('sp_loading') + '</div>';
    try {
      const data = await api('/agents/list');
      const list = data.agents || [];
      if (!list.length) { panel.innerHTML = '<div class="sp-title">' + t('sp_agents') + '</div><div class="sp-empty">' + t('sp_no_agents') + '</div>'; return; }
      const chosen = localStorage.getItem('sases_subagent_agent_id') || '';
      panel.innerHTML = '<div class="sp-title">' + t('sp_agents') + ' <span style="font-weight:400;color:#999;font-size:11px">' + t('sp_default_hint') + '</span></div>' +
        list.map(function (a) {
          const active = String(a.agent_id) === chosen;
          return '<div class="sp-row" data-agent="' + esc(a.agent_id || '') + '" style="cursor:pointer;' +
            (active ? 'background:#eef5ff;' : '') + '"><div class="sp-main"><div class="sp-name">' +
            (active ? '✓ ' : '') + esc(a.name || a.agent_id) +
            '</div><div class="sp-sub">' + esc(a.type || '') + ' · ' + esc(a.agent_id || '') + '</div></div></div>';
        }).join('');
      panel.querySelectorAll('[data-agent]').forEach(function (row) {
        row.onclick = function () {
          localStorage.setItem('sases_subagent_agent_id', row.getAttribute('data-agent'));
          renderAgents();
        };
      });
    } catch (e) { panel.innerHTML = '<div class="sp-title">' + t('sp_agents') + '</div><div class="sp-empty">' + t('sp_load_failed') + '</div>'; }
  }

  function renderPerms() {
    let p = { web: false, write: false, schedule: true };
    try { p = Object.assign(p, JSON.parse(localStorage.getItem('sases_perms_v1') || '{}')); } catch (e) {}
    const row = (k, label, desc) => '<div class="sp-perm"><div><div class="sp-name">' + label +
      '</div><div class="sp-sub">' + desc + '</div></div><input type="checkbox" data-perm="' + k + '" ' + (p[k] ? 'checked' : '') + '></div>';
    panel.innerHTML = '<div class="sp-title">' + t('sp_perms') + '</div>' +
      row('web', t('sp_web'), t('sp_web_desc')) +
      row('write', t('sp_write'), t('sp_write_desc')) +
      row('schedule', t('sp_schedule'), t('sp_schedule_desc'));
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

  const INPUT_MAX_H = 160;   // 最高 160px，超过滚动
  const INPUT_MIN_H = 36;    // 1 行 36px

  function resizeChatInput(input) {
    const el = input || document.getElementById('chat-input');
    if (!el) return;
    el.style.height = 'auto';
    const raw = el.scrollHeight;
    const h = Math.max(INPUT_MIN_H, Math.min(raw, INPUT_MAX_H));
    el.style.height = h + 'px';
    el.style.overflowY = raw > INPUT_MAX_H ? 'auto' : 'hidden';
  }

  function bindInput() {
    const input = document.getElementById('chat-input');
    if (!input || input._spBound) return;
    input._spBound = true;
    const resize = function () { resizeChatInput(input); };
    input.addEventListener('input', resize);
    input.addEventListener('focus', resize);
    // 发送后（点击发送 / 回车）恢复 1 行高度
    const send = document.getElementById('send-btn');
    if (send) send.addEventListener('click', function () { setTimeout(resize, 0); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) setTimeout(resize, 0);
    });
    resize();
  }

  window.sasesResizeChatInput = resizeChatInput;

  window.addEventListener('sases_run_update', function () {
    if (currentType === 'task-pill' && panel) render();
  });

  function boot() {
    ensurePills();
    bindInput();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  document.addEventListener('click', function () { if (currentType) close(); });
  new MutationObserver(boot).observe(document.body, { childList: true, subtree: true });
})();
