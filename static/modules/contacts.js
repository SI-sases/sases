// static/modules/contacts.js
import { api } from './api.js';
import { openChatWindow } from './chat.js';
import { openGroupChat } from './group_chat.js';
import { initPullToRefresh } from './utils.js';
import { t } from './i18n.js';

let initialized = false;
let myAgents = [];
let friendAgents = [];
let touchStartX = 0;
let touchStartY = 0;
let currentOpenRow = null;

export function initContacts() {
  const container = document.getElementById('contacts-list');
  if (!container) return;
  renderContacts(container);
}

function getPinyinInitial(name) {
  if (window.pinyinPro) {
    const pinyin = window.pinyinPro.pinyin(name, { pattern: 'first', toneType: 'none' });
    if (pinyin && pinyin.length > 0) return pinyin[0].toUpperCase();
  }
  return name.charAt(0).toUpperCase();
}

function hashColor(input) {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = input.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}

function getStatusDotClass(agent) {
  if (agent.detail && agent.detail.toLowerCase().includes('offline')) return 'status-dot offline';
  if (agent.detail && agent.detail.toLowerCase().includes('error')) return 'status-dot error';
  return 'status-dot online';
}

async function fetchAgents() {
  try {
    const myData = await api.listMyAgents();
    myAgents = myData.agents || [];
  } catch (e) {
    console.warn('获取智能体列表失败', e);
  }
  try {
    const friendData = await api.listFriendAgents();
    friendAgents = friendData.friends || [];
  } catch (e) {
    console.warn('获取好友智能体失败', e);
  }
}

function generateAgentRow(agent, type) {
  const bgColor = hashColor(agent.agent_id);
  const statusClass = getStatusDotClass(agent);
  const name = type === 'my' ? `${agent.name}${agent.type === 'local' ? ' <span style="color:green;font-size:12px;">授粉+2</span>' : ''}` : agent.name;
  const desc = type === 'my' ? (agent.detail || agent.capability) : `${agent.owner} · ${agent.detail}`;
  const actions = type === 'my' ? `
    <button class="swipe-btn share-btn" data-action="share">${t('share_settings')}</button>
    <button class="swipe-btn delete-btn" data-action="delete">${t('delete')}</button>
  ` : `
    <button class="swipe-btn complain-btn" data-action="complain">${t('complain')}</button>
    <button class="swipe-btn delete-btn" data-action="delete">${t('delete')}</button>
  `;

  return `
    <div class="swipe-row" data-agent-id="${agent.agent_id}" data-agent-name="${agent.name}" data-agent-type="${type}" ${type === 'friend' ? `data-conversation-id="${agent.conversation_id || ''}" data-target-user-id="${agent.target_user_id || ''}"` : ''}>
      <div class="agent-row">
        <div class="agent-avatar" style="background: ${bgColor};">
          ${agent.name.charAt(0)}
          <span class="${statusClass}"></span>
        </div>
        <div class="agent-info">
          <div class="agent-name">${name}</div>
          <div class="agent-desc">${desc}</div>
          <div class="agent-id-display" style="font-size:12px;color:#999;">ID: ${agent.agent_id}</div>
        </div>
      </div>
      <div class="swipe-actions">
        ${actions}
      </div>
    </div>
  `;
}

function closeAllSwipe() {
  if (currentOpenRow) {
    currentOpenRow.classList.remove('swipe-open');
    currentOpenRow = null;
  }
}

function handleTouchStart(e) {
  const touch = e.touches[0];
  touchStartX = touch.clientX;
  touchStartY = touch.clientY;
}

function handleTouchEnd(e) {
  const row = e.currentTarget;
  const touch = e.changedTouches[0];
  const deltaX = touch.clientX - touchStartX;
  const deltaY = touch.clientY - touchStartY;
  if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
    if (deltaX < 0) {
      closeAllSwipe();
      row.classList.add('swipe-open');
      currentOpenRow = row;
    } else {
      row.classList.remove('swipe-open');
      if (currentOpenRow === row) currentOpenRow = null;
    }
  }
}

async function renderContacts(container) {
  container.innerHTML = '<div class="subpage-placeholder">加载中...</div>';
  await fetchAgents();

  let myAgentsHtml = '';
  if (myAgents.length === 0) {
    myAgentsHtml = `<div class="me-menu-item" style="color:#999;">${t('empty_agents')}</div>`;
  } else {
    myAgentsHtml = '<div class="me-menu">';
    myAgents.forEach(agent => {
      myAgentsHtml += generateAgentRow(agent, 'my');
    });
    myAgentsHtml += '</div>';
  }

  let friendAgentsHtml = '';
  let letterIndexHtml = '';
  if (friendAgents.length === 0) {
    friendAgentsHtml = `<div class="me-menu-item" style="color:#999;">${t('no_friend_agents')}</div>`;
  } else {
    const grouped = {};
    friendAgents.forEach(agent => {
      const initial = getPinyinInitial(agent.name);
      if (!grouped[initial]) grouped[initial] = [];
      grouped[initial].push(agent);
    });
    const sortedInitials = Object.keys(grouped).sort();
    friendAgentsHtml = '<div class="me-menu">';
    sortedInitials.forEach(initial => {
      friendAgentsHtml += `<div class="letter-title" data-letter="${initial}">${initial}</div>`;
      grouped[initial].sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN')).forEach(agent => {
        friendAgentsHtml += generateAgentRow(agent, 'friend');
      });
    });
    friendAgentsHtml += '</div>';

    letterIndexHtml = '<div class="letter-index">';
    sortedInitials.forEach(initial => {
      letterIndexHtml += `<div class="letter-index-item" data-letter="${initial}">${initial}</div>`;
    });
    letterIndexHtml += '</div>';
  }

  // 移除多余的单独加好友按钮，保持微信风格
  container.innerHTML = `
    <div class="subpage-search-bar" style="margin-bottom:10px;">
      <input type="text" id="contact-search-input" class="search-input" placeholder="${t('search_placeholder')}">
    </div>
    <div class="me-menu">
      <div class="me-menu-item" data-entry="new-agent">🧑‍🤝‍🧑 添加朋友/智能体</div>
      <div class="me-menu-item" data-entry="api-agent">🔑 ${t('api_agent')}</div>
      <div class="me-menu-item" data-entry="group-chat">👥 ${t('group_chat')}</div>
    </div>
    <div class="section-title">${t('my_agents')}</div>
    ${myAgentsHtml}
    <div class="section-title">${t('friend_agents')}</div>
    <div class="friend-list-wrapper">
      ${friendAgentsHtml}
      ${letterIndexHtml}
    </div>
  `;

  initPullToRefresh(container, async () => {
    await renderContacts(container);
  });

  const searchInput = document.getElementById('contact-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      filterAgents(searchInput.value.trim().toLowerCase());
    });
  }

  container.querySelectorAll('[data-entry]').forEach(item => {
    item.addEventListener('click', () => {
      const type = item.dataset.entry;
      if (type === 'new-agent') {
          if (typeof openNewAgentPage === 'function') openNewAgentPage();
          else window.openSubpage('添加朋友', '<div class="me-menu" style="margin-top:10px;"><div class="me-menu-item"><span class="menu-label" style="padding:20px; display:block; text-align:center; color:#888;">搜索账号功能开发中</span></div></div>', { returnAction: () => window.activateMainView('contacts') });
      }
      else if (type === 'api-agent') { 
          if (window.openModelManagement) window.openModelManagement(() => window.activateMainView('contacts')); 
      }
      else if (type === 'group-chat') {
          if (typeof openGroupChatList === 'function') openGroupChatList();
          else window.openSubpage('群聊', '<div class="me-menu" style="margin-top:10px;"><div class="me-menu-item"><span class="menu-label" style="padding:20px; display:block; text-align:center; color:#888;">群聊列表开发中</span></div></div>', { returnAction: () => window.activateMainView('contacts') });
      }
    });
  });

  try {
    const reqData = await api.getFriendRequests();
    const reqCount = (reqData.requests || []).length;
    if (reqCount > 0) {
      const entry = container.querySelector('[data-entry="new-agent"]');
      if (entry) {
        const badge = document.createElement('span');
        badge.textContent = reqCount;
        badge.style.cssText = 'background:#ff3b30;color:#fff;border-radius:10px;padding:0 6px;font-size:12px;margin-left:auto;';
        entry.appendChild(badge);
      }
    }
  } catch (e) {}

  container.querySelectorAll('.swipe-row').forEach(row => {
    row.addEventListener('click', (e) => {
      if (e.target.closest('.swipe-btn')) return;
      closeAllSwipe();
      const agentId = row.dataset.agentId;
      const agentName = row.dataset.agentName;
      const agentType = row.dataset.agentType;
      
    if (agentType === 'friend') {
      // 好友智能体：弹出名片页
      const convId = row.dataset.conversationId ? parseInt(row.dataset.conversationId) : null;
      const targetUserId = row.dataset.targetUserId ? parseInt(row.dataset.targetUserId) : null;

      let html = '<div style="padding: 40px 20px; text-align: center; background: #fff; min-height: 100vh;">';
      html += '<div style="width: 80px; height: 80px; background: #007aff; color: white; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; font-size: 36px; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,122,255,0.3);">' + agentName.charAt(0) + '</div>';
      html += '<h2 style="margin: 0; font-size: 22px; color: #333;">' + agentName + '</h2>';
      html += '<p style="color: #888; margin-top: 8px; font-size: 14px;">好友智能体</p>';
      html += '<button id="btn-start-chat-from-info" style="margin-top: 40px; width: 100%; padding: 12px; background: #007aff; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer;">发消息</button>';
      html += '</div>';

      if (window.openSubpage) {
        window.openSubpage('详细资料', html, { returnAction: () => window.activateMainView('contacts') });
        setTimeout(() => {
          const btn = document.getElementById('btn-start-chat-from-info');
          if (btn) {
            btn.onclick = () => {
              if (window.closeSubpage) window.closeSubpage();
              setTimeout(() => {
                openChatWindow(convId, agentName, agentId, agentType, 1, 'normal', targetUserId);
              }, 100);
            };
          }
        }, 100);
      }
    } else {
      // 好友智能体：弹出名片页
      const convId = row.dataset.conversationId ? parseInt(row.dataset.conversationId) : null;
      const targetUserId = row.dataset.targetUserId ? parseInt(row.dataset.targetUserId) : null;
      let html = '<div style="padding: 40px 20px; text-align: center; background: #fff; min-height: 100vh;">';
      html += '<div style="width: 80px; height: 80px; background: #007aff; color: white; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; font-size: 36px; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,122,255,0.3);">' + agentName.charAt(0) + '</div>';
      html += '<h2 style="margin: 0; font-size: 22px; color: #333;">' + agentName + '</h2>';
      html += '<p style="color: #888; margin-top: 8px; font-size: 14px;">好友智能体</p>';
      html += '<button id="btn-start-chat-from-info" style="margin-top: 40px; width: 100%; padding: 12px; background: #007aff; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer;">发消息</button>';
      html += '</div>';
      if (window.openSubpage) {
        window.openSubpage('详细资料', html, { returnAction: () => window.activateMainView('contacts') });
        setTimeout(() => {
          const btn = document.getElementById('btn-start-chat-from-info');
          if (btn) {
            btn.onclick = () => {
              if (window.closeSubpage) window.closeSubpage();
              setTimeout(() => {
                openChatWindow(convId, agentName, agentId, agentType, 1, 'normal', targetUserId);
              }, 100);
            };
          }
        }, 100);
      }
    } else {
      // 我的智能体：强开空白会话，不传历史
      openChatWindow(null, agentName, agentId, agentType);
    }
    });

    row.addEventListener('touchstart', handleTouchStart, { passive: true });
    row.addEventListener('touchend', handleTouchEnd, { passive: true });

    const actionBtns = row.querySelectorAll('.swipe-btn');
    actionBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const agentId = row.dataset.agentId;
        const agentName = row.dataset.agentName;
        const agentType = row.dataset.agentType;
        handleSwipeAction(action, agentId, agentName, agentType);
      });
    });
  });

  container.querySelectorAll('.letter-index-item').forEach(item => {
    item.addEventListener('click', () => {
      const letter = item.dataset.letter;
      const titleElements = container.querySelectorAll('.letter-title');
      for (const titleEl of titleElements) {
        if (titleEl.textContent === letter) {
          titleEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
          break;
        }
      }
    });
  });
}

function handleSwipeAction(action, agentId, agentName, agentType) {
  closeAllSwipe();
  if (action === 'share') {
    alert(t('share_settings') + ': ' + agentName);
  } else if (action === 'delete') {
    if (confirm(`${t('delete_confirm')} "${agentName}"?`)) {
      alert(t('delete_success'));
      renderContacts(document.getElementById('contacts-list'));
    }
  } else if (action === 'complain') {
    alert(t('complain') + ' ' + t('coming_soon'));
  }
}

function filterAgents(query) {
  const container = document.getElementById('contacts-list');
  if (!container) return;
  const rows = container.querySelectorAll('.swipe-row');
  rows.forEach(row => {
    const name = row.dataset.agentName?.toLowerCase() || '';
    const desc = row.querySelector('.agent-desc')?.textContent?.toLowerCase() || '';
    const match = name.includes(query) || desc.includes(query);
    row.style.display = match ? '' : 'none';
  });
  const titles = container.querySelectorAll('.letter-title');
  titles.forEach(title => {
    let next = title.nextElementSibling;
    let hasVisible = false;
    while (next && !next.classList.contains('letter-title')) {
      if (next.classList.contains('swipe-row') && next.style.display !== 'none') {
        hasVisible = true;
        break;
      }
      next = next.nextElementSibling;
    }
    title.style.display = hasVisible ? '' : 'none';
  });
}

// ==================== 添加朋友 / 智能体页（参考微信） ====================
function openNewAgentPage() {
  const contentHtml = `
    <div style="padding: 10px 0;">
      <div style="background: #fff; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
        <div style="font-weight: 600; margin-bottom: 10px; font-size: 15px;">🔍 添加新好友 (通过 SASES ID)</div>
        <div style="display: flex; gap: 8px;">
          <input type="text" class="search-input" id="add-user-input" placeholder="输入对方 SASES ID (如 sases_xxx)" style="flex:1;">
          <button class="search-btn" id="add-user-btn">添加</button>
        </div>
      </div>

      <div style="background: #fff; border-radius: 8px; padding: 15px;">
        <div style="font-weight: 600; margin-bottom: 10px; font-size: 15px;">🤖 搜索并添加智能体</div>
        <div class="subpage-search-bar" style="margin-bottom:0;">
          <input type="text" class="search-input" id="agent-search-input" placeholder="搜索智能体名称...">
          <button class="search-btn" id="search-agent-btn">搜索</button>
        </div>
        <div id="agent-search-results" class="me-menu" style="margin-top: 10px;"></div>
      </div>

      <div class="section-title" style="margin-top:20px;">${t('request_received')}</div>
      <div id="friend-requests-list" class="me-menu"></div>
    </div>
  `;
  
  window.openSubpage('添加朋友', contentHtml, {
    showMore: false,
    returnAction: () => window.activateMainView('contacts')
  });

  setTimeout(() => {
    // 添加用户事件
    document.getElementById('add-user-btn').addEventListener('click', async () => {
      const sasesId = document.getElementById('add-user-input').value.trim();
      if (!sasesId) return alert('请输入 SASES ID');
      
      try {
        const res = await fetch('/agents/friend-request', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + localStorage.getItem('sases_token')
          },
          body: JSON.stringify({ target_sases_id: sasesId })
        });
        const data = await res.json();
        if (res.ok) alert('✅ 好友请求已发送，等待对方同意！');
        else alert('❌ 发送失败: ' + (data.detail || data.message || '未知错误'));
      } catch (e) {
        alert('网络错误: ' + e.message);
      }
    });

    // 搜索智能体事件
    document.getElementById('search-agent-btn').addEventListener('click', () => {
      const q = document.getElementById('agent-search-input').value.trim();
      if (q) searchAgents(q);
    });
    document.getElementById('agent-search-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && document.getElementById('agent-search-input').value.trim()) {
        searchAgents(document.getElementById('agent-search-input').value.trim());
      }
    });
    
    loadFriendRequests();
  }, 100);
}

async function searchAgents(q) {
  const resultsContainer = document.getElementById('agent-search-results');
  resultsContainer.innerHTML = '<div class="subpage-placeholder">搜索中...</div>';
  try {
    const data = await api.searchAgents(q, true);
    const results = data.results || [];
    if (results.length === 0) {
      resultsContainer.innerHTML = '<div class="subpage-placeholder">无结果</div>';
      return;
    }
    let html = '';
    results.forEach(agent => {
      html += `
        <div class="me-menu-item agent-row" data-agent-id="${agent.agent_id}" data-agent-name="${agent.name}" data-price="${agent.price}">
          <div class="agent-avatar" style="background: ${hashColor(agent.agent_id)};">${agent.name.charAt(0)}</div>
          <div class="agent-info">
            <div class="agent-name">${agent.name}</div>
            <div class="agent-desc">${agent.owner} · ${agent.detail}</div>
            <div class="agent-id-display" style="font-size:12px;color:#999;">ID: ${agent.agent_id}</div>
          </div>
          <button class="add-friend-btn" data-agent-id="${agent.agent_id}">${t('add_friend')}</button>
        </div>
      `;
    });
    resultsContainer.innerHTML = html;

    resultsContainer.querySelectorAll('.add-friend-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const agentId = btn.dataset.agentId;
        // 注意：这里调用的是加智能体的旧API，如果需要区分，可以在 api.sendFriendRequest 里传 agent_id
        await sendFriendRequest(agentId);
      });
    });
  } catch (e) {
    resultsContainer.innerHTML = `<div class="subpage-placeholder">搜索失败：${e.message}</div>`;
  }
}

async function sendFriendRequest(agentId) {
  try {
    // 这里保持原有逻辑（假设 api.js 里有这个方法）
    await api.sendFriendRequest(agentId);
    alert(t('request_sent'));
  } catch (e) {
    alert(t('send_failed') + ': ' + e.message);
  }
}

async function loadFriendRequests() {
  const container = document.getElementById('friend-requests-list');
  if (!container) return;
  container.innerHTML = '<div class="subpage-placeholder">加载中...</div>';
  try {
    const data = await api.getFriendRequests();
    const requests = data.requests || [];
    if (requests.length === 0) {
      container.innerHTML = `<div class="subpage-placeholder">暂无好友请求</div>`;
      return;
    }
    let html = '';
    requests.forEach(req => {
      html += `
        <div class="me-menu-item friend-request-item">
          <div class="agent-avatar">${req.requester_name ? req.requester_name.charAt(0) : '?'}</div>
          <div class="agent-info">
            <div class="agent-name">${req.requester_name || '未知用户'}</div>
            <div class="agent-desc">请求添加您为好友</div>
          </div>
          <button class="accept-request-btn" data-request-id="${req.id}" style="background:#007aff;color:#fff;border:none;padding:4px 10px;border-radius:4px;">同意</button>
          <button class="reject-request-btn" data-request-id="${req.id}" style="margin-left:4px;">拒绝</button>
        </div>
      `;
    });
    container.innerHTML = html;

    container.querySelectorAll('.accept-request-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const requestId = btn.dataset.requestId;
        try {
          await api.acceptFriendRequest(requestId);
          alert(t('accepted') || '已同意');
          loadFriendRequests();
        } catch (err) { alert('操作失败: ' + err.message); }
      });
    });
    container.querySelectorAll('.reject-request-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const requestId = btn.dataset.requestId;
        try {
          await api.rejectFriendRequest(requestId);
          alert(t('rejected') || '已拒绝');
          loadFriendRequests();
        } catch (err) { alert('操作失败: ' + err.message); }
      });
    });
  } catch (e) {
    container.innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

// ==================== 群聊列表 ====================
async function openGroupChatList() {
  let groupsHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage(t('group_chat'), groupsHtml);

  try {
    const data = await api.listMyGroups();
    const groups = data.groups || [];
    if (groups.length === 0) {
      groupsHtml = `<div class="subpage-placeholder">${t('no_groups')}</div>`;
    } else {
      groupsHtml = '<div class="me-menu">';
      groups.forEach(group => {
        groupsHtml += `
          <div class="me-menu-item group-item" data-group-id="${group.id}" data-group-name="${group.name}">
            <span class="menu-icon">👥</span>
            <div class="menu-text">
              <div class="menu-title">${group.name}</div>
              <div class="menu-desc">${group.member_count} ${t('member_count')}</div>
            </div>
          </div>
        `;
      });
      groupsHtml += '</div>';
    }
  } catch (e) {
    groupsHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <input type="text" id="new-group-name" class="market-input" placeholder="${t('group_name')}" style="flex:1;">
      <button id="create-group-btn" class="save-btn" style="width:auto;">${t('create_group')}</button>
    </div>
    ${groupsHtml}
  `;
  document.getElementById('subpage-content').innerHTML = contentHtml;

  const createBtn = document.getElementById('create-group-btn');
  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      const name = document.getElementById('new-group-name').value.trim();
      if (!name) { alert(t('please_input_all')); return; }
      try {
        await api.createGroup(name);
        alert(t('create_group_success'));
        openGroupChatList();
      } catch (e) {
        alert(t('create_group_failed') + ': ' + e.message);
      }
    });
  }

  document.querySelectorAll('.group-item').forEach(item => {
    item.addEventListener('click', () => {
      const groupId = item.dataset.groupId;
      const groupName = item.dataset.groupName;
      window.currentGroupChat = true;
      openGroupChat(groupId, groupName);
      window.closeSubpage();
    });
  });
}

// 导出全局
window.openNewAgentPage = openNewAgentPage;
window.openGroupChatList = openGroupChatList;