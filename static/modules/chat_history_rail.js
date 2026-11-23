// static/modules/chat_history_rail.js
// 右侧「最近会话」迷你历史栏（DeepSeek 风格），独立模块，可插拔：
//   window.SASES.chatHistoryRail = { refresh, toggle, open }
// 依赖：api.listConversations / api.listMyGroups / chat.openChatWindow / group_chat.openGroupChat

import { api } from './api.js';
import { openChatWindow, chatState } from './chat.js';
import { openGroupChat, closeGroupChat } from './group_chat.js';

const STORE_KEY = 'sases_chat_rail_collapsed';
const MAX_ITEMS = 40;

let _rail = null;
let _listEl = null;
let _openBtn = null;
let _loading = false;
let _lastCid = null;
let _collapsed = false;
let _lastRefresh = 0;

try { _collapsed = localStorage.getItem(STORE_KEY) === '1'; } catch (e) { _collapsed = false; }
if (window.innerWidth < 720 && localStorage.getItem(STORE_KEY) === null) _collapsed = true;

function _injectStyle() {
  if (document.getElementById('chr-style')) return;
  const css = `
#chat-history-rail{position:absolute;right:10px;top:50%;transform:translateY(-50%);
  width:198px;max-height:58vh;background:rgba(255,255,255,.97);border:1px solid rgba(0,0,0,.08);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  border-radius:12px;box-shadow:0 6px 22px rgba(0,0,0,.10);z-index:12;display:flex;
  flex-direction:column;overflow:hidden;font-size:12px;font-family:system-ui,-apple-system,sans-serif}
#chat-history-rail .chr-head{display:flex;align-items:center;gap:6px;padding:8px 10px;
  border-bottom:1px solid rgba(0,0,0,.06);font-weight:600;color:#333;cursor:pointer;user-select:none}
#chat-history-rail .chr-head .chr-dot{width:6px;height:6px;border-radius:50%;background:#007aff}
#chat-history-rail .chr-head .chr-count{flex:1;font-weight:400;color:#999;font-size:11px}
#chat-history-rail .chr-list{overflow-y:auto;padding:4px;overscroll-behavior:contain}
#chat-history-rail .chr-empty{padding:14px 10px;color:#999;text-align:center}
#chat-history-rail .chr-sec{padding:6px 8px 2px;color:#aaa;font-size:10px;letter-spacing:.5px}
#chat-history-rail .chr-item{display:flex;align-items:center;gap:6px;padding:6px 7px;
  border-radius:8px;cursor:pointer;transition:background .12s}
#chat-history-rail .chr-item:hover{background:rgba(0,122,255,.08)}
#chat-history-rail .chr-item.active{background:rgba(0,122,255,.13);box-shadow:inset 2px 0 0 #007aff}
#chat-history-rail .chr-avatar{flex:0 0 20px;width:20px;height:20px;border-radius:6px;
  background:#e8f0fe;color:#1a73e8;display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:600}
#chat-history-rail .chr-main{flex:1;min-width:0}
#chat-history-rail .chr-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#222}
#chat-history-rail .chr-sub{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  color:#9aa0a6;font-size:10px;margin-top:1px}
#chat-history-rail .chr-time{flex:0 0 auto;color:#9aa0a6;font-size:10px}
#chat-history-rail .chr-unread{flex:0 0 auto;min-width:14px;height:14px;padding:0 4px;
  border-radius:7px;background:#ff3b30;color:#fff;font-size:9px;display:flex;
  align-items:center;justify-content:center}
#chat-rail-open{position:absolute;right:0;top:50%;transform:translateY(-50%);z-index:12;
  writing-mode:vertical-rl;padding:10px 4px;background:rgba(255,255,255,.94);
  border:1px solid rgba(0,0,0,.08);border-right:none;border-radius:8px 0 0 8px;
  color:#007aff;font-size:11px;cursor:pointer;box-shadow:-2px 0 8px rgba(0,0,0,.06);
  font-family:system-ui,-apple-system,sans-serif}
@media (min-width:900px){
  .chat-window.rail-open .chat-messages{padding-right:214px}
}
@media (max-width:560px){
  #chat-history-rail{width:164px;max-height:50vh}
}
`;
  const style = document.createElement('style');
  style.id = 'chr-style';
  style.textContent = css;
  document.head.appendChild(style);
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
  _injectStyle();
  if (_rail && _rail.isConnected) return true;

  _rail = _el('div');
  _rail.id = 'chat-history-rail';

  const head = _el('div', 'chr-head');
  head.appendChild(_el('span', 'chr-dot'));
  head.appendChild(_el('span', null, t('chr_recent')));
  head.appendChild(_el('span', 'chr-count', ''));
  head.title = t('chr_collapse');
  head.onclick = () => _applyCollapsed(true, true);
  _rail.appendChild(head);

  _listEl = _el('div', 'chr-list');
  _rail.appendChild(_listEl);

  _openBtn = _el('div', null, t('chr_history'));
  _openBtn.id = 'chat-rail-open';
  _openBtn.title = t('chr_expand_recent');
  _openBtn.onclick = () => _applyCollapsed(false, true);

  win.appendChild(_rail);
  win.appendChild(_openBtn);
  _applyCollapsed(_collapsed, false);
  return true;
}

function _applyCollapsed(v, persist) {
  _collapsed = !!v;
  if (persist) {
    try { localStorage.setItem(STORE_KEY, _collapsed ? '1' : '0'); } catch (e) {}
  }
  const win = document.getElementById('view-chat-window');
  if (_rail) _rail.style.display = _collapsed ? 'none' : 'flex';
  if (_openBtn) _openBtn.style.display = _collapsed ? 'block' : 'none';
  if (win) win.classList.toggle('rail-open', !_collapsed);
}

function _relTime(iso) {
  if (!iso) return '';
  let t = String(iso).replace(' ', 'T');
  const d = new Date(t);
  if (isNaN(d.getTime())) return '';
  const diff = Math.max(0, Date.now() - d.getTime());
  const m = Math.floor(diff / 60000);
  if (m < 1) return t('chr_just_now');
  if (m < 60) return m + '分';
  const h = Math.floor(m / 60);
  if (h < 24) return h + '时';
  const day = Math.floor(h / 24);
  if (day < 30) return day + '天';
  return (d.getMonth() + 1) + '/' + d.getDate();
}

function _renderItem(c) {
  const item = _el('div', 'chr-item');
  if (_lastCid != null && String(c.id) === String(_lastCid)) item.classList.add('active');
  const title = c.title || '会话';
  item.title = title + (c.last_message ? '\n' + String(c.last_message).slice(0, 120) : '');

  item.appendChild(_el('div', 'chr-avatar', title.slice(0, 1)));
  const main = _el('div', 'chr-main');
  main.appendChild(_el('div', 'chr-title', title));
  const sub = (c.last_sender_name ? c.last_sender_name + '：' : '') + (c.last_message || '');
  main.appendChild(_el('div', 'chr-sub', String(sub).slice(0, 60)));
  item.appendChild(main);
  item.appendChild(_el('div', 'chr-time', _relTime(c.updated_at)));
  if (c.unread_count > 0) item.appendChild(_el('div', 'chr-unread', String(c.unread_count)));

  item.onclick = () => {
    try {
      if (window.currentGroupChat) closeGroupChat();
      openChatWindow(c.id, title, c.agent_id || null, 'my',
        Number(c.is_friend_chat) || 0, c.friend_mode || 'normal', c.target_user_id || null);
    } catch (e) {
      console.error('[chat-rail] open failed', e);
    }
  };
  return item;
}

function _renderGroup(g) {
  const item = _el('div', 'chr-item');
  item.title = g.name || '群聊';
  item.appendChild(_el('div', 'chr-avatar', (g.name || '群').slice(0, 1)));
  const main = _el('div', 'chr-main');
  main.appendChild(_el('div', 'chr-title', g.name || '群聊'));
  main.appendChild(_el('div', 'chr-sub', String(g.last_message || '').slice(0, 60)));
  item.appendChild(main);
  if (g.unread_count > 0) item.appendChild(_el('div', 'chr-unread', String(g.unread_count)));
  item.onclick = () => {
    try { openGroupChat(g.id, g.name || '群聊'); } catch (e) { console.error('[chat-rail] group open failed', e); }
  };
  return item;
}

function _paint(convs, groups) {
  if (!_listEl) return;
  _listEl.innerHTML = '';
  const count = _listEl.parentElement.querySelector('.chr-count');
  if (count) count.textContent = convs.length ? String(convs.length) : '';

  if (!convs.length && !groups.length) {
    _listEl.appendChild(_el('div', 'chr-empty', '暂无历史会话'));
    return;
  }
  convs.forEach(c => _listEl.appendChild(_renderItem(c)));
  if (groups.length) {
    _listEl.appendChild(_el('div', 'chr-sec', '群聊'));
    groups.forEach(g => _listEl.appendChild(_renderGroup(g)));
  }
}

export async function refreshChatRail() {
  if (_loading) return;
  if (!_ensure()) return;
  _loading = true;
  try {
    const [convData, groupData] = await Promise.all([
      api.listConversations().catch(() => ({ conversations: [] })),
      api.listMyGroups().catch(() => ({ groups: [] })),
    ]);
    const convs = (convData.conversations || []).slice(0, MAX_ITEMS);
    const groups = (groupData.groups || []).slice(0, 8);
    _paint(convs, groups);
    _lastRefresh = Date.now();
  } finally {
    _loading = false;
  }
}

function _tick() {
  if (!_ensure()) return;
  const cid = window.chatState ? window.chatState.conversationId : null;
  if (String(cid) !== String(_lastCid)) {
    _lastCid = cid;
    refreshChatRail();
    return;
  }
  if (!_collapsed && document.visibilityState !== 'hidden' && Date.now() - _lastRefresh > 30000) {
    refreshChatRail();
  }
}

let _msgTimer = null;
window.addEventListener('sases_new_message', () => {
  if (_msgTimer) clearTimeout(_msgTimer);
  _msgTimer = setTimeout(() => refreshChatRail(), 600);
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => setTimeout(refreshChatRail, 800));
} else {
  setTimeout(refreshChatRail, 800);
}
setInterval(_tick, 1200);

window.SASES = window.SASES || {};
window.SASES.chatHistoryRail = {
  refresh: refreshChatRail,
  toggle: () => _applyCollapsed(!_collapsed, true),
  open: () => _applyCollapsed(false, true),
};
