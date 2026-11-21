// static/modules/chat_trace.js
// P3-C3: 任务执行追踪子窗口（监听 sases_task_trace）

let _panel = null;
let _body = null;
let _runId = null;
let _collapsed = false;
let _rows = 0;
const MAX_ROWS = 60;

const ICONS = {
  success: '✅', failed: '❌', error: '❌', retry: '⚠️',
  timeout: '⏱', skipped: '⏭', paused: '⏸',
};

function _ensurePanel() {
  if (_panel) return;
  _panel = document.createElement('div');
  _panel.id = 'task-trace-panel';
  _panel.style.cssText = [
    'position:fixed', 'right:16px', 'bottom:88px', 'width:330px',
    'max-height:42vh', 'z-index:9998', 'background:rgba(20,22,28,.94)',
    'color:#e8eaed', 'border:1px solid rgba(255,255,255,.12)', 'border-radius:10px',
    'box-shadow:0 8px 28px rgba(0,0,0,.45)', 'font:12px/1.5 Consolas,Menlo,monospace',
    'display:flex', 'flex-direction:column', 'overflow:hidden',
  ].join(';');

  const head = document.createElement('div');
  head.style.cssText = 'display:flex;align-items:center;gap:8px;padding:8px 10px;background:rgba(255,255,255,.06);cursor:pointer';
  const title = document.createElement('span');
  title.id = 'task-trace-title';
  title.textContent = '执行追踪';
  title.style.cssText = 'flex:1;font-weight:600;font-family:system-ui,sans-serif';
  const closeBtn = document.createElement('span');
  closeBtn.textContent = '×';
  closeBtn.style.cssText = 'cursor:pointer;font-size:16px;line-height:1;opacity:.7;font-family:system-ui,sans-serif';
  closeBtn.onclick = (ev) => { ev.stopPropagation(); _panel.style.display = 'none'; };
  head.appendChild(title);
  head.appendChild(closeBtn);
  head.onclick = () => {
    _collapsed = !_collapsed;
    _body.style.display = _collapsed ? 'none' : 'block';
  };

  _body = document.createElement('div');
  _body.style.cssText = 'padding:6px 10px 10px;overflow-y:auto;white-space:pre-wrap;word-break:break-all';

  _panel.appendChild(head);
  _panel.appendChild(_body);
  document.body.appendChild(_panel);
}

function _reset(runId) {
  _ensurePanel();
  _panel.style.display = 'flex';
  _collapsed = false;
  _body.style.display = 'block';
  _body.innerHTML = '';
  _rows = 0;
  _runId = runId;
  const t = document.getElementById('task-trace-title');
  if (t) t.textContent = '执行追踪 · run ' + (runId == null ? '?' : runId);
}

function _add(d) {
  const icon = ICONS[d.status] || '•';
  const total = d.total || '?';
  const tool = d.tool || 'step';
  const ms = d.duration_ms != null ? d.duration_ms + 'ms' : '';
  const line = document.createElement('div');
  line.style.cssText = 'padding:2px 0;border-bottom:1px dashed rgba(255,255,255,.06)';
  const color = d.status === 'success' ? '#7ee787' : (d.status === 'failed' || d.status === 'error' ? '#ff7b72' : '#e3b341');
  line.innerHTML =
    '<span style="color:' + color + '">' + icon + '</span> ' +
    '<span style="opacity:.65">[' + (d.step != null ? d.step : '?') + '/' + total + ']</span> ' +
    '<span>' + _esc(tool) + '</span> ' +
    '<span style="opacity:.55">' + ms + '</span>';
  if (d.output_preview) {
    const p = document.createElement('div');
    p.style.cssText = 'opacity:.45;margin-left:18px;font-size:11px';
    p.textContent = String(d.output_preview).slice(0, 120);
    line.appendChild(p);
  }
  _body.appendChild(line);
  _rows += 1;
  while (_rows > MAX_ROWS && _body.firstChild) {
    _body.removeChild(_body.firstChild);
    _rows -= 1;
  }
  _body.scrollTop = _body.scrollHeight;
}

function _esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

window.addEventListener('sases_task_trace', (e) => {
  const d = e.detail || {};
  const cid = window.chatState && window.chatState.conversationId;
  if (cid && d.conversation_id && String(cid) !== String(d.conversation_id)) return;
  if (_runId !== d.run_id) _reset(d.run_id);
  _add(d);
});

window.sasesTraceClear = function () {
  if (_panel) _panel.style.display = 'none';
  _rows = 0;
  _runId = null;
};
