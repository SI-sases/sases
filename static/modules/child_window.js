// static/modules/child_window.js
// One drawer for subagents, background tasks and approvals.
const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem('sases_token') || '';

const state = {
  open: false,
  tab: 'agents',
  agents: [],
  tasks: [],
  approvals: [],
  timer: null,
  selected: null,
  messages: {},
};

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

async function getJSON(path) {
  const r = await fetch(path, { headers: { 'Authorization': 'Bearer ' + token() } });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

async function postJSON(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token() },
    body: JSON.stringify(body || {})
  });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

function statusText(s) {
  return ({ active: '运行中', running: '运行中', done: '已完成', failed: '失败',
    cancelled: '已取消', queued: '排队中', needs_approval: '待审批' })[s] || s || '未知';
}

function activeCount() {
  const live = (x) => x.status === 'active' || x.status === 'queued';
  return state.agents.filter(live).length + state.tasks.filter(live).length;
}

function badgeCount() {
  return activeCount() + state.approvals.length;
}

export function renderChildWindow() {
  const badge = $('child-menu-badge');
  if (badge) {
    const n = badgeCount();
    badge.textContent = String(n);
    badge.hidden = n === 0;
  }
  const ca = $('child-count-agents');
  const ct = $('child-count-tasks');
  const cp = $('child-count-approvals');
  if (ca) ca.textContent = String(state.agents.filter((a) => a.status === 'active' || a.status === 'queued').length);
  if (ct) ct.textContent = String(state.tasks.filter((t) => t.status === 'active').length);
  if (cp) cp.textContent = String(state.approvals.length);
  renderCapsules();
  renderPanel();
}

function renderCapsules() {
  const box = $('subagent-capsules');
  if (!box) return;
  const items = [
    ...state.agents.filter((a) => a.status === 'active' || a.status === 'queued').slice(0, 2).map((a) => ({
      label: '🤖 ' + (a.name || a.goal || '子智能体'), tab: 'agents', id: a.agent_id
    })),
    ...state.tasks.filter((t) => t.status === 'active' || t.status === 'queued').slice(0, 1).map((t) => ({
      label: '⚙ ' + (t.name || t.goal || '后台任务'), tab: 'tasks', id: t.agent_id
    }))
  ];
  box.innerHTML = items.map((it) =>
    `<button class="subagent-capsule running" data-capsule-tab="${it.tab}" data-capsule-id="${esc(it.id)}">` +
    `<span class="dot"></span>${esc(it.label)}</button>`).join('');
  box.querySelectorAll('[data-capsule-tab]').forEach((btn) => {
    btn.onclick = () => {
      state.tab = btn.dataset.capsuleTab;
      state.selected = btn.dataset.capsuleId;
      openChildWindow(state.tab, state.selected);
    };
  });
}

function agentCard(a, kind) {
  const id = a.agent_id || '';
  const st = statusText(a.status);
  const active = a.status === 'active';
  const canCancel = (active || a.status === 'queued') && kind === 'agents';
  const msgs = state.messages[id];
  return `<div class="child-agent-card" data-agent-card="${esc(id)}">
    <div class="child-agent-top">
      <div class="child-agent-name">${kind === 'tasks' ? '⚙ ' : '🤖 '}${esc(a.name || a.goal || '未命名')}</div>
      <div class="child-agent-status ${active ? 'active' : ''}">${esc(st)}</div>
    </div>
    <div class="child-agent-goal">${esc(a.goal || a.task_json || '')}</div>
    <div class="child-agent-meta">${esc(a.progress || '')}${a.progress ? ' · ' : ''}${esc(a.node_id || '-')}${a.trace_id ? ' · ' + esc(a.trace_id) : ''}</div>
    <div class="child-agent-actions">
      <button data-act="messages" data-id="${esc(id)}">消息</button>
      ${a.status === 'queued' ? `<button data-act="run" data-id="${esc(id)}">执行</button>` : ''}
      ${canCancel ? `<button class="danger" data-act="cancel" data-id="${esc(id)}">取消</button>` : ''}
    </div>
    ${msgs ? `<div class="child-message-list">${msgs.length ? msgs.map((m) =>
      `<div class="child-message"><b>${esc(m.direction === 'parent_to_child' ? '我' : '子')}</b> ${esc(m.payload_json || '')}</div>`).join('') :
      '<div class="child-message">暂无消息</div>'}</div>
      <div class="child-steer-row"><input data-steer-input="${esc(id)}" placeholder="发消息纠偏…"><button data-act="steer" data-id="${esc(id)}">发送</button></div>` : ''}
  </div>`;
}

function renderPanel() {
  const body = $('child-window-body');
  if (!body) return;
  document.querySelectorAll('.child-tab').forEach((b) => {
    b.classList.toggle('active', b.dataset.childTab === state.tab);
  });
  if (state.tab === 'approvals') {
    body.innerHTML = state.approvals.length ? state.approvals.map((a) =>
      `<div class="child-approval-card"><div class="child-agent-name">⚠️ ${esc(a.description || a.tool)}</div>
       <div class="child-approval-desc">风险：${esc(a.risk || 'high')} · ${esc(a.tool || '')}</div>
       <button class="primary" data-approve="${a.id}" data-decision="allow">允许</button>
       <button data-approve="${a.id}" data-decision="deny">拒绝</button></div>`).join('') :
      '<div class="child-empty">没有待审批项</div>';
    body.querySelectorAll('[data-approve]').forEach((btn) => {
      btn.onclick = async () => {
        try {
          await postJSON('/agi/approvals/decide', { id: Number(btn.dataset.approve), decision: btn.dataset.decision });
          await refreshChildWindow();
        } catch (e) { btn.disabled = true; }
      };
    });
    return;
  }
  const rows = state.tab === 'tasks' ? state.tasks : state.agents;
  if (!rows.length) {
    body.innerHTML = state.tab === 'tasks' ?
      '<div class="child-empty">没有后台任务</div>' :
      '<div class="child-empty">还没有子智能体<br>让主 AGI 派一个任务试试</div>';
    return;
  }
  body.innerHTML = rows.map((a) => agentCard(a, state.tab)).join('');
  body.querySelectorAll('[data-act="messages"]').forEach((btn) => {
    btn.onclick = async () => {
      btn.disabled = true;
      try {
        const data = await getJSON(`/agi/agents/${encodeURIComponent(btn.dataset.id)}/messages`);
        state.messages[btn.dataset.id] = data.messages || [];
        renderPanel();
      } catch (e) { btn.disabled = false; }
    };
  });
  body.querySelectorAll('[data-act="run"]').forEach((btn) => {
    btn.onclick = async () => {
      btn.disabled = true;
      try { await postJSON('/agi/worker/run', {}); await refreshChildWindow(); }
      catch (e) { btn.disabled = false; }
    };
  });
  body.querySelectorAll('[data-act="cancel"]').forEach((btn) => {
    btn.onclick = async () => {
      if (!confirm('取消这个子智能体？')) return;
      try {
        await postJSON(`/agi/agents/${encodeURIComponent(btn.dataset.id)}/cancel`, {});
        await refreshChildWindow();
      } catch (e) { btn.disabled = true; }
    };
  });
  body.querySelectorAll('[data-act="steer"]').forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.dataset.id;
      const input = body.querySelector(`[data-steer-input="${CSS.escape(id)}"]`);
      const text = (input && input.value || '').trim();
      if (!text) return;
      try {
        await postJSON(`/agi/agents/${encodeURIComponent(id)}/message`, { message: text });
        input.value = '';
        const data = await getJSON(`/agi/agents/${encodeURIComponent(id)}/messages`);
        state.messages[id] = data.messages || [];
        renderPanel();
      } catch (e) { btn.disabled = true; }
    };
  });
}

export async function refreshChildWindow() {
  try {
    const [agents, tasks, approvals] = await Promise.all([
      getJSON('/agi/agents'),
      getJSON('/agi/background-tasks'),
      getJSON('/agi/approvals')
    ]);
    state.agents = agents.agents || [];
    state.tasks = tasks.tasks || [];
    state.approvals = approvals.approvals || [];
    renderChildWindow();
  } catch (e) {
    const body = $('child-window-body');
    if (body && state.open) {
      body.innerHTML = '<div class="child-empty">主 AGI 暂不可用<br>稍后再试</div>';
    }
  }
}

export function openChildWindow(tab = 'agents', selected = null) {
  const win = $('child-window');
  if (!win) return;
  state.open = true;
  state.tab = tab || 'agents';
  state.selected = selected || null;
  win.style.display = 'block';
  win.setAttribute('aria-hidden', 'false');
  requestAnimationFrame(() => win.classList.add('open'));
  refreshChildWindow();
  if (state.timer) clearInterval(state.timer);
  state.timer = setInterval(() => {
    if (state.open && !document.hidden) refreshChildWindow();
  }, 2500);
}

export function closeChildWindow() {
  const win = $('child-window');
  if (!win) return;
  state.open = false;
  win.classList.remove('open');
  win.setAttribute('aria-hidden', 'true');
  setTimeout(() => { win.style.display = 'none'; }, 200);
  if (state.timer) { clearInterval(state.timer); state.timer = null; }
}

export function initChildWindow() {
  const menu = $('menu-child-window');
  if (menu) menu.onclick = () => {
    try { window.closeSideDrawer && window.closeSideDrawer(); } catch (e) {}
    const drawer = $('side-drawer');
    if (drawer) { drawer.classList.remove('open'); setTimeout(() => drawer.style.display = 'none', 250); }
    openChildWindow('agents');
  };
  const close = $('child-window-close');
  if (close) close.onclick = closeChildWindow;
  const overlay = $('child-window-overlay');
  if (overlay) overlay.onclick = closeChildWindow;
  document.querySelectorAll('.child-tab').forEach((btn) => {
    btn.onclick = () => { state.tab = btn.dataset.childTab; renderPanel(); };
  });
  window.addEventListener('sases_child_update', () => refreshChildWindow());
  window.addEventListener('sases_new_message', () => {
    if (state.open) refreshChildWindow();
  });
  refreshChildWindow();
}

if (typeof window !== 'undefined') {
  window.openChildWindow = openChildWindow;
  window.closeChildWindow = closeChildWindow;
  window.refreshChildWindow = refreshChildWindow;
}
