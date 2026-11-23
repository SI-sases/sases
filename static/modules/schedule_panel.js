// static/modules/schedule_panel.js
// 定时任务面板：#5 的可视化版本（每天 / 每周 / 每 N 小时），创建时保存胶囊快照
import { openSubpage } from './subpage.js';

let _root = null;

function _token() { return localStorage.getItem('sases_token') || ''; }

async function _json(path, opts) {
  const r = await fetch(path, opts);
  let data = null;
  try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw new Error((data && (data.detail || data.message)) || ('HTTP ' + r.status));
  return data;
}

function _css() {
  if (document.getElementById('sched-style')) return;
  const s = document.createElement('style');
  s.id = 'sched-style';
  s.textContent = `
#sched-root{padding:12px;font-family:system-ui,-apple-system,sans-serif;font-size:13px;color:#222}
.sched-card{background:#fff;border:1px solid #eee;border-radius:10px;padding:12px;margin-bottom:12px}
.sched-card h3{margin:0 0 8px;font-size:14px}
.sched-row{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
.sched-input{flex:1;min-width:120px;border:1px solid #ddd;border-radius:6px;padding:6px 8px;font-size:12px}
.sched-btn{border:1px solid #ddd;background:#fff;border-radius:6px;padding:5px 10px;cursor:pointer;font-size:12px}
.sched-btn.primary{background:#007aff;border-color:#007aff;color:#fff}
.sched-item{display:flex;gap:8px;align-items:center;padding:8px 4px;border-bottom:1px solid #f4f4f4}
.sched-item:last-child{border-bottom:none}
.sched-main{flex:1;min-width:0}
.sched-name{font-weight:600}
.sched-sub{color:#999;font-size:11px;margin-top:2px}
.sched-badge{font-size:10px;padding:1px 6px;border-radius:8px;background:#eef4ff;color:#1a73e8;margin-left:6px}
.sched-badge.off{background:#f2f2f2;color:#888}
.sched-empty{color:#999;text-align:center;padding:16px}
.sched-err{color:#d93025;font-size:12px;margin-top:6px}
`;
  document.head.appendChild(s);
}

function _currentCid() {
  return (window.chatState && window.chatState.conversationId) || null;
}

function _snapshot() {
  return {
    apis: (window.currentSessionAPIs || []).slice(),
    tools: (window.currentSessionTools || []).slice(),
    skills: (window.currentSessionSkills || []).slice(),
  };
}

function _cron(freq, time, weekday, interval) {
  const parts = (time || '05:00').split(':');
  const h = Math.max(0, Math.min(23, parseInt(parts[0], 10) || 0));
  const m = Math.max(0, Math.min(59, parseInt(parts[1], 10) || 0));
  if (freq === 'weekly') return m + ' ' + h + ' * * ' + String(weekday);
  if (freq === 'interval') return m + ' */' + String(Math.max(1, interval || 6)) + ' * * *';
  return m + ' ' + h + ' * * *';
}

function _listHtml(tasks) {
  if (!tasks.length) return `<div class="sched-empty">${t('sch_empty')}</div>`;
  let html = '';
  tasks.forEach(t => {
    const on = t.enabled ? '' : 'off';
    html += `<div class="sched-item" data-id="${t.id}">
      <div class="sched-main">
        <div class="sched-name">${_esc(t.name || t.task_template)}<span class="sched-badge ${on}">${t.enabled ? t('sch_running') : t('sch_paused')}</span></div>
        <div class="sched-sub">${_esc(t.task_template)} · ${_esc(t.cron_expr)} · ${t('sch_next')} ${_esc((t.next_run_at || '').replace('T', ' ').slice(0, 16))}</div>
      </div>
      <button class="sched-btn" data-act="toggle">${t.enabled ? t('sch_pause') : t('sch_enable')}</button>
      <button class="sched-btn" data-act="delete" style="color:#d93025">${t('sch_delete')}</button>
    </div>`;
  });
  return html;
}

function _esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function _refresh() {
  try {
    const data = await _json('/scheduled/list', { headers: { Authorization: 'Bearer ' + _token() } });
    const box = document.getElementById('sched-list');
    if (box) {
      box.innerHTML = _listHtml(data.tasks || []);
      box.querySelectorAll('.sched-item').forEach(el => {
        const id = el.dataset.id;
        const del = el.querySelector('[data-act="delete"]');
        const tog = el.querySelector('[data-act="toggle"]');
        if (del) del.onclick = async () => {
          if (!confirm(t('sch_delete_confirm'))) return;
          await _json('/scheduled/' + id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + _token() } });
          _refresh();
        };
        if (tog) tog.onclick = async () => {
          const paused = el.querySelector('.sched-badge').classList.contains('off');
          await _json('/scheduled/' + id + '/toggle', {
            method: 'PATCH',
            headers: { Authorization: 'Bearer ' + _token(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: paused }),
          });
          _refresh();
        };
      });
    }
  } catch (e) {
    const box = document.getElementById('sched-list');
    if (box) box.innerHTML = '<div class="sched-err">加载失败：' + _esc(e.message) + '</div>';
  }
}

export async function openSchedule() {
  _css();
  openSubpage('定时任务', `
    <div id="sched-root">
      <div class="sched-card">
        <h3>新建定时任务</h3>
        <div class="sched-row"><input class="sched-input" id="sched-template" placeholder="到点要做什么，例如：整理今天的邮件"></div>
        <div class="sched-row">
          <select class="sched-input" id="sched-freq" style="flex:0 0 110px">
            <option value="daily">每天</option>
            <option value="weekly">每周</option>
            <option value="interval">每 N 小时</option>
          </select>
          <input class="sched-input" id="sched-time" type="time" value="05:00" style="flex:0 0 110px">
          <select class="sched-input" id="sched-weekday" style="flex:0 0 100px;display:none">
            <option value="0">周一</option><option value="1">周二</option><option value="2">周三</option>
            <option value="3">周四</option><option value="4">周五</option><option value="5">周六</option><option value="6">周日</option>
          </select>
          <input class="sched-input" id="sched-interval" type="number" min="1" max="23" value="6" style="flex:0 0 80px;display:none">
        </div>
        <div class="sched-row">
          <button class="sched-btn primary" id="sched-create">创建</button>
          <span class="sched-err" id="sched-err"></span>
        </div>
        <div class="sched-sub" id="sched-snap"></div>
      </div>
      <div class="sched-card"><h3>我的定时任务</h3><div id="sched-list"><div class="sched-empty">加载中...</div></div></div>
    </div>`);
  _root = document.getElementById('sched-root');

  const snap = _snapshot();
  const snapEl = document.getElementById('sched-snap');
  if (snapEl) snapEl.textContent = '胶囊快照：工具 ' + snap.tools.length + ' / API ' + snap.apis.length + ' / 技能 ' + snap.skills.length;

  const freq = document.getElementById('sched-freq');
  const weekday = document.getElementById('sched-weekday');
  const interval = document.getElementById('sched-interval');
  const timeEl = document.getElementById('sched-time');
  freq.onchange = () => {
    weekday.style.display = freq.value === 'weekly' ? 'block' : 'none';
    interval.style.display = freq.value === 'interval' ? 'block' : 'none';
    timeEl.style.display = freq.value === 'interval' ? 'none' : 'block';
  };

  const btn = document.getElementById('sched-create');
  btn.onclick = async () => {
    const err = document.getElementById('sched-err');
    const template = document.getElementById('sched-template').value.trim();
    const cid = _currentCid();
    const sid = (window.chatState && (window.chatState.senderAgentId || window.chatState.agentId)) || '';
    if (!template) { err.textContent = '请填写任务内容'; return; }
    if (!cid) { err.textContent = '请先打开一个会话'; return; }
    if (!sid) { err.textContent = '请先在会话里选择接单智能体'; return; }
    const cron = _cron(freq.value, timeEl.value, weekday.value, parseInt(interval.value, 10));
    try {
      await _json('/scheduled/create', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + _token(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: template.slice(0, 12),
          cron_expr: cron,
          task_template: template,
          conversation_id: cid,
          supervisor_id: sid,
          timezone: 'Asia/Shanghai',
          capsule_snapshot: _snapshot(),
        }),
      });
      err.textContent = '已创建';
      document.getElementById('sched-template').value = '';
      _refresh();
    } catch (e) {
      err.textContent = e.message;
    }
  };

  _refresh();
}

window.SASES = window.SASES || {};
window.SASES.schedule = { open: openSchedule };
