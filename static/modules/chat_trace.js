// static/modules/chat_trace.js
// 任务执行追踪：任意聊天窗口都可打开的后台任务抽屉（run_trace 持久化）
// 对外：window.SASES.chatTrace = { open, close, refresh }

const API = {
  active: (cid) => `/supervisor/runs/active?conversation_id=${cid}`,
  recent: (cid, limit = 10) => `/supervisor/runs/recent?conversation_id=${cid}&limit=${limit}`,
  events: (runId, afterSeq = 0) => `/trace/${runId}/events?after_seq=${afterSeq}`,
};

let _drawer = null;
let _body = null;
let _chip = null;
let _select = null;
let _title = null;
let _detailToggle = null;
let _cid = null;
let _runId = null;
let _lastSeq = 0;
let _events = [];
let _runs = [];
let _pollTimer = null;
let _lastConversation = null;

function _token() {
  return localStorage.getItem('sases_token') || '';
}

async function _get(path) {
  const r = await fetch(path, { headers: { Authorization: 'Bearer ' + _token() } });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

function _style() {
  if (document.getElementById('trace-style')) return;
  const css = `
#trace-chip{position:absolute;right:12px;top:58px;z-index:14;display:none;
  align-items:center;gap:6px;padding:6px 10px;border-radius:16px;cursor:pointer;
  background:rgba(0,122,255,.92);color:#fff;font-size:12px;box-shadow:0 4px 12px rgba(0,122,255,.28);
  font-family:system-ui,-apple-system,sans-serif}
#trace-chip .dot{width:6px;height:6px;border-radius:50%;background:#fff;animation:tracePulse 1.6s infinite}
@keyframes tracePulse{0%,100%{opacity:.35}50%{opacity:1}}
#trace-drawer{position:absolute;top:52px;right:0;bottom:0;width:380px;max-width:92vw;z-index:30;
  background:#fff;border-left:1px solid rgba(0,0,0,.08);box-shadow:-8px 0 24px rgba(0,0,0,.08);
  display:flex;flex-direction:column;transform:translateX(102%);transition:transform .18s ease;
  font-family:system-ui,-apple-system,sans-serif;font-size:12px}
#trace-drawer.open{transform:translateX(0)}
#trace-drawer .tr-head{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid #eee}
#trace-drawer .tr-title{font-weight:600;color:#222;flex:1}
#trace-drawer select{border:1px solid #ddd;border-radius:6px;padding:3px 6px;font-size:12px;max-width:150px}
#trace-drawer .tr-close{cursor:pointer;font-size:18px;color:#888;line-height:1}
#trace-drawer .tr-tools{display:flex;align-items:center;gap:10px;padding:6px 12px;border-bottom:1px solid #f0f0f0;color:#777}
#trace-drawer .tr-list{flex:1;overflow-y:auto;padding:8px 10px}
#trace-drawer .tr-empty{color:#999;text-align:center;padding:24px 0}
.tr-row{display:flex;gap:8px;padding:6px 6px;border-radius:8px;align-items:flex-start}
.tr-row:hover{background:#f7f9fc}
.tr-row .lv{flex:0 0 26px;text-align:center;font-size:10px;color:#888;padding-top:2px}
.tr-row .st{flex:0 0 auto;font-size:13px}
.tr-row .ct{flex:1;min-width:0;color:#333;white-space:pre-wrap;word-break:break-word;line-height:1.5}
.tr-row .tm{flex:0 0 auto;color:#aaa;font-size:10px;padding-top:2px}
.tr-row.l3,.tr-row.l4{display:none}
#trace-drawer.show-detail .tr-row.l3,#trace-drawer.show-detail .tr-row.l4{display:flex}
.chat-window.trace-open .chat-messages{padding-right:392px}
@media (max-width:900px){#trace-drawer{width:100%}.chat-window.trace-open .chat-messages{padding-right:0}}
.chat-window.trace-open #chat-history-rail{display:none !important}
`;
  const s = document.createElement('style');
  s.id = 'trace-style';
  s.textContent = css;
  document.head.appendChild(s);
}

function _el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function _ensure() {
  const win = document.getElementById('view-chat-window');
  if (!win) return false;
  _style();
  if (_drawer && _drawer.isConnected) return true;

  _chip = _el('div', null);
  _chip.id = 'trace-chip';
  _chip.innerHTML = '<span class="dot"></span><span class="txt">后台任务</span>';
  _chip.onclick = () => open();
  win.appendChild(_chip);

  _drawer = _el('div');
  _drawer.id = 'trace-drawer';

  const head = _el('div', 'tr-head');
  _title = _el('span', 'tr-title', '执行追踪');
  _select = document.createElement('select');
  _select.onchange = () => {
    const id = parseInt(_select.value || '0', 10);
    if (id) _loadRun(id);
  };
  const closeBtn = _el('span', 'tr-close', '×');
  closeBtn.onclick = () => close();
  head.appendChild(_title);
  head.appendChild(_select);
  head.appendChild(closeBtn);

  const tools = _el('div', 'tr-tools');
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.onchange = () => _drawer.classList.toggle('show-detail', cb.checked);
  _detailToggle = cb;
  tools.appendChild(cb);
  tools.appendChild(_el('span', null, '显示 L3/L4 细节'));
  const artBtn = document.createElement('button');
  artBtn.id = 'trace-artifacts-btn';
  artBtn.textContent = '产物';
  artBtn.style.cssText = 'margin-left:auto;border:1px solid #ddd;background:#fff;border-radius:6px;padding:2px 8px;font-size:11px;cursor:pointer';
  artBtn.onclick = () => _loadArtifacts();
  tools.appendChild(artBtn);

  _body = _el('div', 'tr-list');
  _drawer.appendChild(head);
  _drawer.appendChild(tools);
  _drawer.appendChild(_body);
  win.appendChild(_drawer);
  return true;
}

const _ICONS = { success: '✅', failed: '❌', error: '❌', retry: '⚠️', timeout: '⏱', running: '⏳', paused: '⏸', completed: '✅' };

function _row(ev) {
  const row = _el('div', 'tr-row l' + (ev.level || 1));
  row.appendChild(_el('div', 'lv', 'L' + (ev.level || 1)));
  row.appendChild(_el('div', 'st', _ICONS[ev.status] || '•'));
  const ct = _el('div', 'ct');
  ct.textContent = ev.content || ev.event_type || '';
  if (ev.tool) {
    const tag = _el('span', null, '  [' + ev.tool + ']');
    tag.style.color = '#999';
    ct.appendChild(tag);
  }
  row.appendChild(ct);
  const t = String(ev.created_at || '');
  row.appendChild(_el('div', 'tm', t.length >= 16 ? t.slice(11, 16) : ''));
  return row;
}

async function _loadArtifacts() {
  if (!_body) return;
  if (!_runId) { _body.innerHTML = '<div class="tr-empty">当前没有任务</div>'; return; }
  _body.innerHTML = '<div class="tr-empty">加载产物…</div>';
  try {
    const d = await _get('/supervisor/runs/' + _runId + '/artifacts');
    const list = d.artifacts || [];
    _body.innerHTML = '';
    const back = document.createElement('div');
    back.textContent = '← 返回轨迹';
    back.style.cssText = 'padding:6px 8px;color:#007aff;cursor:pointer;font-size:12px';
    back.onclick = () => _paint();
    _body.appendChild(back);
    if (!list.length) {
      _body.appendChild(_el('div', 'tr-empty', '本次任务没有产物'));
      return;
    }
    for (const a of list) {
      const row = _el('div', 'tr-row');
      const link = document.createElement('a');
      link.href = a.path || '#';
      link.target = '_blank';
      link.textContent = a.name || a.path;
      link.style.cssText = 'color:#007aff;word-break:break-all;font-size:12px';
      row.appendChild(link);
      if (a.kind) row.appendChild(_el('span', 'tm', a.kind));
      _body.appendChild(row);
    }
  } catch (e) {
    _body.innerHTML = '<div class="tr-empty">产物加载失败</div>';
  }
}

function _paint() {
  if (!_body) return;
  _body.innerHTML = '';
  if (!_events.length) {
    _body.appendChild(_el('div', 'tr-empty', _runId ? '暂无轨迹（任务刚开始）' : '当前窗口没有可查看的任务'));
    return;
  }
  for (const ev of _events) _body.appendChild(_row(ev));
  _body.scrollTop = _body.scrollHeight;
}

function _paintRuns() {
  if (!_select) return;
  _select.innerHTML = '';
  if (!_runs.length) return;
  for (const r of _runs) {
    const opt = document.createElement('option');
    opt.value = String(r.id);
    const st = r.status === 'running' ? '执行中' : (r.status === 'completed' ? '完成' : r.status);
    opt.textContent = '#' + r.id + ' ' + st + ' · ' + String(r.goal || '').slice(0, 18);
    _select.appendChild(opt);
  }
  _select.value = String(_runId || _runs[0].id);
}

async function _loadRun(runId) {
  _runId = runId;
  _lastSeq = 0;
  _events = [];
  _title.textContent = '执行追踪 · run ' + runId;
  _paint();
  try {
    const data = await _get(API.events(runId, 0) + '&limit=1000');
    _events = data.events || [];
    _lastSeq = _events.length ? _events[_events.length - 1].seq : 0;
    _paint();
  } catch (e) {
    console.warn('[trace] load events failed', e);
  }
}

async function _loadRuns() {
  if (!_cid) return;
  try {
    const [rec, act] = await Promise.all([
      _get(API.recent(_cid, 10)),
      _get(API.active(_cid)),
    ]);
    _runs = rec.runs || [];
    const active = act.runs || [];
    _updateChip(active.length);
    if (!_runId && _runs.length) _runId = _runs[0].id;
    _paintRuns();
  } catch (e) {
    console.warn('[trace] load runs failed', e);
  }
}

function _updateChip(n) {
  if (!_chip) return;
  _chip.style.display = n > 0 ? 'flex' : 'none';
  const txt = _chip.querySelector('.txt');
  if (txt) txt.textContent = '后台任务 ' + n;
}

export async function open() {
  if (!_ensure()) return;
  const cid = window.chatState && window.chatState.conversationId;
  if (!cid) return;
  _cid = cid;
  const win = document.getElementById('view-chat-window');
  if (win) win.classList.add('trace-open');
  _drawer.classList.add('open');
  await _loadRuns();
  if (_runs.length) {
    const active = _runs.find(r => ['running', 'running_resumed', 'paused', 'proposed'].includes(r.status)) || _runs[0];
    await _loadRun(active.id);
  } else {
    _paint();
  }
  _startPoll();
}

export function close() {
  if (_drawer) _drawer.classList.remove('open');
  const win = document.getElementById('view-chat-window');
  if (win) win.classList.remove('trace-open');
  _stopPoll();
}

export async function refresh() {
  if (!_ensure()) return;
  const cid = window.chatState && window.chatState.conversationId;
  if (!cid) return;
  _cid = cid;
  await _loadRuns();
}

function _startPoll() {
  _stopPoll();
  _pollTimer = setInterval(() => {
    if (_drawer && _drawer.classList.contains('open')) {
      _loadRuns();
    }
  }, 5000);
}

function _stopPoll() {
  if (_pollTimer) clearInterval(_pollTimer);
  _pollTimer = null;
}

window.addEventListener('sases_task_trace', (e) => {
  const d = e.detail || {};
  if (!_cid || String(d.conversation_id) !== String(_cid)) return;
  if (d.run_id === _runId && d.seq) {
    if (d.seq <= _lastSeq) return;
    _lastSeq = d.seq;
    _events.push({
      seq: d.seq, level: d.level || 2, event_type: d.event_type || 'step_done',
      tool: d.tool, status: d.status, content: d.output_preview, created_at: new Date().toISOString(),
    });
    _paint();
  }
  _loadRuns();
});

// 会话切换检测
setInterval(() => {
  const cid = window.chatState && window.chatState.conversationId;
  if (String(cid) !== String(_lastConversation)) {
    _lastConversation = cid;
    _runId = null;
    _events = [];
    _lastSeq = 0;
    if (cid) {
      _ensure();
      refresh();
    } else {
      _updateChip(0);
      close();
    }
  }
}, 1200);

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => setTimeout(_ensure, 900));
} else {
  setTimeout(_ensure, 900);
}

window.SASES = window.SASES || {};
window.SASES.chatTrace = { open, close, refresh };
