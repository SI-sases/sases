// static/modules/messages.js
import { api } from './api.js';
import { openChatWindow } from './chat.js';
import { openGroupChat } from './group_chat.js';
import { initPullToRefresh } from './utils.js';
import { t } from './i18n.js';

let initialized = false;

if (!window._sasesMsgListenerBound) {
  window._sasesMsgListenerBound = true;
  window.addEventListener('sases_new_message', () => {
    const container = document.getElementById('messages-list');
    if (container && document.getElementById('view-messages').classList.contains('active')) {
      loadConversations(container);
    }
  });
}

export async function initMessages() {
  const container = document.getElementById('messages-list');
  if (!container) return;
  if (initialized) return;
  initialized = true;
  await loadConversations(container);

  // 渲染新手引导卡片
  if (typeof window.onboarding?.renderCard === 'function') {
    try {
      await window.onboarding.renderCard();
    } catch (e) {
      console.warn('渲染引导卡片失败', e);
    }
  }
}

async function loadConversations(container) {
  try {
    const [convData, groupData] = await Promise.all([
      api.listConversations(),
      api.listMyGroups()
    ]);

    const conversations = convData.conversations || [];
    const groups = groupData.groups || [];

    if (conversations.length === 0 && groups.length === 0) {
      container.innerHTML = `<div class="empty">${t('no_conversations')}</div>`;
      return;
    }

    let html = '';

    // 安全转义函数，防止 XSS 和 HTML 结构破坏
    const escapeHtml = (str) => {
      if (!str) return '';
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };

    // ================= 渲染单聊会话 =================
    conversations.forEach(conv => {
      const agentName = escapeHtml(conv.title || '会话');
      const lastMessage = escapeHtml(conv.last_message || '');
      const unread = conv.unread_count || 0;
      const pinned = conv.is_pinned ? 'pinned' : '';
      const pinnedVal = conv.is_pinned ? 1 : 0;
      const lastSenderName = escapeHtml(conv.last_sender_name || '');
      const displayLast = lastSenderName ? `${lastSenderName}: ${lastMessage}` : lastMessage;

      html += `
        <div class="session-item ${pinned}" data-type="single" data-conversation-id="${conv.id}" data-agent-id="${conv.agent_id || ''}" data-title="${agentName}" data-target-user-id="${conv.target_user_id || ''}" data-is-friend="${conv.is_friend_chat || 0}" data-friend-mode="${conv.friend_mode || 'normal'}">
          <div class="session-avatar">
            ${agentName.charAt(0)}
            ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ''}
          </div>
          <div class="session-info">
            <div class="session-name">${agentName}</div>
            <div class="session-last">${displayLast}</div>
          </div>
          <button class="session-more-btn" data-type="single" data-id="${conv.id}" data-pinned="${pinnedVal}">⋯</button>
        </div>
      `;
    });

    // ================= 渲染群聊会话 =================
    const _hiddenGroups = (() => { try { return JSON.parse(localStorage.getItem('sases_hidden_groups') || '[]'); } catch(e) { return []; } })();

    groups.forEach(group => {
      const groupName = escapeHtml(group.name || '群聊');
      const lastMessage = escapeHtml(group.last_message || '');
      const lastSenderName = escapeHtml(group.last_sender_name || '');
      const displayLast = lastSenderName ? `${lastSenderName}: ${lastMessage}` : lastMessage;
      const groupId = group.id;
      if (_hiddenGroups.map(String).includes(String(groupId))) return;

      const _groupPinned = group.is_pinned ? 'pinned' : '';
      const _groupUnread = group.unread_count || 0;
      
      html += `
        <div class="session-item ${_groupPinned}" data-type="group" data-group-id="${groupId}" data-title="${groupName}" data-pinned="${group.is_pinned ? 1 : 0}">
          <div class="session-avatar">
            ${groupName.charAt(0)}
            ${_groupUnread > 0 ? `<span class="unread-badge">${_groupUnread}</span>` : ''}
          </div>
          <div class="session-info">
            <div class="session-name">${groupName}</div>
            <div class="session-last">${displayLast}</div>
          </div>
          <button class="session-more-btn" data-type="group" data-id="${groupId}">⋯</button>
        </div>
      `;
    });

    container.innerHTML = html;

    // ... 下面的点击事件绑定保持不变 ...
    initPullToRefresh(container, async () => {
      await loadConversations(container);
    });

    // ================= 绑定点击事件 =================
    container.querySelectorAll('.session-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.session-more-btn')) return;
        const type = item.dataset.type;
        
        // 上报新手引导动作：打开会话视为完成"发送消息"任务的前置
        if (typeof window.onboarding?.report === 'function') {
          window.onboarding.report('send_message');
        }
        
        if (type === 'single') {
          const conversationId = item.dataset.conversationId;
          const agentId = item.dataset.agentId || null;
          const title = item.dataset.title;
          const agentType = item.dataset.agentType || 'my';
          const isFriendChat = parseInt(item.dataset.isFriend || 0);
          const friendMode = item.dataset.friendMode || 'normal';
          
          // 把 is_friend_chat 和 friend_mode 透传给聊天窗口
          const targetUserId = parseInt(item.dataset.targetUserId || 0) || null;
          openChatWindow(conversationId, title, agentId, agentType, isFriendChat, friendMode, targetUserId);
        } else if (type === 'group') {
          const groupId = item.dataset.groupId;
          const title = item.dataset.title;
          openGroupChat(groupId, title);
        }
      });
    });

    container.querySelectorAll('.session-more-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const type = btn.dataset.type;
        const id = btn.dataset.id;
        if (type === 'single') {
          const pinned = btn.dataset.pinned === '1' ? true : false;
          showSingleSessionActions(id, pinned, btn);
        } else if (type === 'group') {
          showGroupSessionActions(id, btn);
        }
      });
    });
  } catch (e) {
    console.error('loadConversations error:', e);
    container.innerHTML = `<div class="empty">${t('load_failed')}: ${e.message}</div>`;
  }
}

function showSessionMenu(btn, items, onSelect) {
  const old = document.getElementById('__session_menu__');
  if (old && old.__sourceBtn === btn) {
    old.remove();
    return;
  }
  if (old) old.remove();
  const menu = document.createElement('div');
  menu.className = 'session-menu';
  menu.id = '__session_menu__';
  menu.__sourceBtn = btn;
  items.forEach(item => {
    const el = document.createElement('div');
    el.className = 'session-menu-item' + (item.danger ? ' danger' : '');
    el.textContent = item.label;
    el.onclick = (e) => { e.stopPropagation(); menu.remove(); onSelect(item.action); };
    menu.appendChild(el);
  });
  document.body.appendChild(menu);
  const r = btn.getBoundingClientRect();
  menu.style.top = (r.bottom + 4) + 'px';
  menu.style.left = Math.max(8, r.right - menu.offsetWidth) + 'px';
  setTimeout(() => {
    const closer = (e) => {
      if (btn.contains(e.target)) return;
      menu.remove();
      document.removeEventListener('click', closer);
    };
    document.addEventListener('click', closer);
  }, 0);
}

function showSingleSessionActions(conversationId, pinned, btn) {
  if (btn && typeof showSessionMenu === 'function') {
    showSessionMenu(btn, [
      { label: pinned ? '取消置顶' : '置顶', action: 'pin' },
      { label: '标记已读', action: 'read' },
      { label: '删除会话', action: 'delete', danger: true }
    ], function (a) {
      if (a === 'pin') togglePin(conversationId, !pinned);
      else if (a === 'read') markRead(conversationId);
      else if (a === 'delete') deleteConversation(conversationId);
    });
    return;
  }
  const action = prompt(
    `${t('choose_action')}\n1. ${pinned ? t('unpin') : t('pin')}\n2. ${t('mark_read')}\n3. ${t('delete_conversation')}\n0. ${t('cancel')}`
  );
  if (action === '1') {
    togglePin(conversationId, !pinned);
  } else if (action === '2') {
    markRead(conversationId);
  } else if (action === '3') {
    deleteConversation(conversationId);
  }
}

function showGroupSessionActions(groupId, btn) {
  const pinned = btn && btn.dataset && btn.dataset.pinned === '1';
  if (btn && typeof showSessionMenu === 'function') {
    showSessionMenu(btn, [
      { label: pinned ? '取消置顶' : '置顶群聊', action: 'pin' },
      { label: '标记已读', action: 'read' },
      { label: '删除（本地隐藏）', action: 'delete', danger: true }
    ], function (a) {
      if (a === 'read') {
        api.markGroupRead(groupId).then(() => location.reload()).catch(e => alert('操作失败: ' + (e.message || '')));
        return;
      }
      if (a === 'pin') {
        api.togglePinGroup(groupId, !pinned).then(() => location.reload()).catch(e => alert('操作失败: ' + (e.message || '')));
        return;
      }
      if (a === 'delete') {
        try {
          const list = JSON.parse(localStorage.getItem('sases_hidden_groups') || '[]').map(String);
          const _gid = String(groupId);
          if (!list.includes(_gid)) list.push(_gid);
          localStorage.setItem('sases_hidden_groups', JSON.stringify(list));
        } catch(e) {}
        if (btn && btn.closest('.session-item')) btn.closest('.session-item').remove();
      }
    });
    return;
  }
  const action = prompt('选择操作：\n1. 删除群聊（本地隐藏）\n0. 取消');
  if (action === '1') {
    try {
      const list = JSON.parse(localStorage.getItem('sases_hidden_groups') || '[]').map(String);
      const _gid = String(groupId);
      if (!list.includes(_gid)) list.push(_gid);
      localStorage.setItem('sases_hidden_groups', JSON.stringify(list));
    } catch(e) {}
    if (btn && btn.closest('.session-item')) btn.closest('.session-item').remove();
  }
}

async function togglePin(conversationId, pinned) {
  try {
    await api.togglePinConversation(conversationId, pinned);
    location.reload();
  } catch (e) {
    alert(t('operation_failed') + ': ' + e.message);
  }
}

async function markRead(conversationId) {
  try {
    await api.markConversationRead(conversationId);
    location.reload();
  } catch (e) {
    alert(t('operation_failed') + ': ' + e.message);
  }
}

async function deleteConversation(conversationId) {
  if (!confirm(t('delete_confirm'))) return;
  try {
    await api.deleteConversation(conversationId);
    location.reload();
  } catch (e) {
    alert(t('delete_failed') + ': ' + e.message);
  }
}

async function quitGroup(groupId) {
  if (!confirm('确定退出该群聊吗？')) return;
  try {
    await api.removeGroupMember(groupId, 'self');
    location.reload();
  } catch (e) {
    alert(t('operation_failed') + ': ' + e.message);
  }
}