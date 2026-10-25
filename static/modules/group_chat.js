// static/modules/group_chat.js
import { api } from './api.js';
import { showGroupToast } from './group_toast.js';
import { openGroupFiles } from './group_file_ui.js';
import './group_knowledge_ui.js';
import './group_redpacket_ui.js';
import './group_task_ui.js';
import './group_swarm_ui.js';
import './group_manage_ui.js';
import './group_report_ui.js';

let currentGroupId = null;
let currentGroupName = '';
let currentAgentId = null; // 当前使用的智能体身份，null 表示用户本人
let currentGroupMode = 'normal'; // normal 或 swarm
let currentUserId = null; // 当前登录用户ID
// ======================================================================
// 【模块 0. 调试接口】
// ======================================================================

window._gcDebug = { getUserId: () => currentUserId, getAgentId: () => currentAgentId, getGroupId: () => currentGroupId };

// ======================================================================
// 【模块 1. 群聊主入口与生命周期】
// ======================================================================

export async function openGroupChat(groupId, groupName) {
  currentGroupId = groupId;

  // 先获取当前用户ID
  try {
    const _me = await api.getMe();
    currentUserId = _me.user_id;
  } catch (_e) {
    currentUserId = null;
  }

  // 从 localStorage 读取该用户的群模式
  try {
    currentGroupMode = localStorage.getItem('sases_group_mode_' + groupId) || 'normal';
  } catch (e) {
    currentGroupMode = 'normal';
  }

  window.currentGroupId = groupId;
  currentGroupName = groupName;
  window.currentGroupChat = true;

  // 恢复当前模式对应的身份
  try {
    const _saved = localStorage.getItem('sases_agent_' + currentGroupMode + '_' + groupId) || '';
    currentAgentId = _saved || null;
  } catch (e) {
    currentAgentId = null;
  }

  try {
    const _sn = localStorage.getItem('sases_agent_name_' + currentGroupMode + '_' + groupId) || '';
    const _b = document.getElementById('identity-btn');
    if (currentAgentId && _sn) {
      if (_b) { _b.textContent = _sn.substring(0,2); _b.style.background = '#07c160'; _b.style.color = '#fff'; _b.style.borderRadius = '50%'; _b.style.width = '32px'; _b.style.height = '32px'; _b.style.display = 'flex'; _b.style.alignItems = 'center'; _b.style.justifyContent = 'center'; _b.style.fontSize = '11px'; _b.style.fontWeight = '600'; }
      document.getElementById('chat-window-title').textContent = groupName + ' (' + _sn + ')';
    } else {
      if (_b) { _b.textContent = '🤖'; _b.style.background = 'none'; _b.style.color = ''; }
      document.getElementById('chat-window-title').textContent = groupName;
    }
  } catch (e) {
    document.getElementById('chat-window-title').textContent = groupName;
  }
  const _mt0 = document.getElementById('chat-mode-text');
  if (_mt0) _mt0.textContent = currentGroupMode === 'normal' ? '普通聊天' : '蜂群模式';
  document.getElementById('view-chat-window').style.display = 'flex';
  document.querySelector('.bottom-nav').style.display = 'none';
  document.querySelector('.top-bar').style.display = 'none';

  const settingsBtn = document.getElementById('group-settings-btn');
  if (settingsBtn) {
    settingsBtn.style.display = 'block';
    settingsBtn.onclick = openGroupSettings;
  }

  let identityBtn = document.getElementById('identity-btn');
  if (identityBtn) {
    identityBtn.style.display = 'block';
    const _newBtn = identityBtn.cloneNode(true);
    identityBtn.parentNode.replaceChild(_newBtn, identityBtn);
    identityBtn = _newBtn;
    identityBtn.onclick = () => openAgentSwitch(true);
  }

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    modeBtn.style.display = 'block';
    modeBtn.onclick = openGroupModeMenu;
  }
  const _plusBtn = document.getElementById('input-plus-btn');
  if (_plusBtn) {
    _plusBtn.onclick = () => {
      import('./chat_menu.js').then(m => m.toggleChatPlusPanel());
    };
  }
  const _chatInput = document.getElementById('chat-input');
  if (_chatInput) {
    _chatInput.oninput = () => {
      if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
    };
  }
  let _sendBtn = document.getElementById('send-btn');
  if (_sendBtn) {
    const _newSend = _sendBtn.cloneNode(true);
    _sendBtn.parentNode.replaceChild(_newSend, _sendBtn);
    _sendBtn = _newSend;
    _sendBtn.onclick = sendGroupMessage;
  }

  loadGroupTasks();
  if (window.loadGroupRedPackets) window.loadGroupRedPackets();


  const messagesContainer = document.getElementById('chat-messages');
  // 建立 WebSocket 连接
  try {
    if (window._groupWs) {
      window._groupWs.close();
      window._groupWs = null;
    }
    api.getGroupInfo(groupId).then(info => {
      const ggid = info && info.global_group_id;
      if (!ggid) return;
      const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/group/' + encodeURIComponent(ggid);
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d && d.type === 'message') {
            // 自己发的消息已乐观渲染，跳过
            if (d.sender_id && String(d.sender_id) === String(currentUserId) && !d.sender_agent_id) {
              return;
            }
            // 增量追加
            const _container = document.getElementById('chat-messages');
            if (_container) {
              appendGroupMessage(d.sender_name || '?', d.content, false);
            }
          }
        } catch (err) {}
      };
      ws.onopen = () => console.log('[ws] connected to', ggid);
      ws.onclose = () => console.log('[ws] disconnected');
      window._groupWs = ws;
    }).catch(() => {});
  } catch (e) {
    console.warn('[ws] setup failed:', e);
  }
  messagesContainer.innerHTML = '';
  loadGroupMessages();
}

export function closeGroupChat() {
  currentGroupId = null;

  window.currentGroupId = null;
  currentGroupName = '';
  currentAgentId = null;
  currentUserId = null;
  window.currentGroupChat = false;

  document.getElementById('view-chat-window').style.display = 'none';
  document.querySelector('.bottom-nav').style.display = 'flex';
  document.querySelector('.top-bar').style.display = 'flex';

  const settingsBtn = document.getElementById('group-settings-btn');
  if (settingsBtn) settingsBtn.style.display = 'none';
  const identityBtn = document.getElementById('identity-btn');
  if (identityBtn) identityBtn.style.display = 'none';
  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) modeBtn.style.display = 'none';
}

// ======================================================================
// 【模块 2. 群任务（横条/列表）】
// ======================================================================

async function loadGroupTasks() {
  if (!currentGroupId) return;
  try {
    const data = await api.getGroupTasks(currentGroupId, 'open');
    const tasks = data.tasks || [];
    const bar = document.getElementById('group-task-bar');
    const text = document.getElementById('group-task-bar-text');
    if (!bar || !text) return;
    if (tasks.length === 0) {
      bar.style.display = 'none';
      return;
    }
    text.textContent = '进行中任务 (' + tasks.length + ')';
    bar.style.display = 'flex';
    bar.onclick = function() {
      openTaskListPage(tasks);
    };
  } catch (e) {
    console.log('loadGroupTasks error:', e);
  }
}

function openTaskListPage(tasks) {
  let html = '<div style="padding:12px;">';
  tasks.forEach(t => {
    html += '<div class="task-list-item" data-tid="' + t.id + '" style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;cursor:pointer;">';
    html += '<div style="font-size:15px;font-weight:600;margin-bottom:4px;">' + (t.title || '未命名') + '</div>';
    html += '<div style="font-size:12px;color:#666;">质押 ' + (t.reward_credits || 0) + ' 积分 · ' + (t.task_category || 'text') + '</div>';
    html += '</div>';
  });
  html += '</div>';
  window.openSubpage('进行中任务', html);
  setTimeout(function() {
    document.querySelectorAll('.task-list-item').forEach(el => {
      el.onclick = function() {
        if (typeof window.openTaskDetail === 'function') window.openTaskDetail(parseInt(el.dataset.tid));
      };
    });
  }, 300);
}


// ======================================================================
// 【模块 3. 通用工具（Toast）】
// ======================================================================

// showGroupToast 已迁移到 group_toast.js，通过 import 使用



// ======================================================================
// 【模块 4. 群红包（抢/拆/列表）】
// ======================================================================

window.openGroupRedPacket = async function(packetId) {
  try {
    const detail = await fetch('/group/red-packets/' + packetId, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    }).then(r => r.json());
    if (detail.error || detail.detail) { alert('加载失败：' + (detail.error || detail.detail)); return; }
    let claimsHtml = '';
    if (detail.claims && detail.claims.length > 0) {
      claimsHtml = '<div style="margin-top:20px;"><div style="font-size:13px;color:#999;margin-bottom:8px;">领取记录</div>';
      detail.claims.forEach(c => {
        claimsHtml += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f5f5f5;font-size:13px;"><span>' + (c.username || '匿名') + '</span><span style="color:#f59e0b;font-weight:600;">' + c.amount + ' 积分</span></div>';
      });
      claimsHtml += '</div>';
    }
    let bodyHtml = '';
    if (detail.claimed_by_me !== null && detail.claimed_by_me !== undefined) {
      bodyHtml = '<div style="font-size:48px;font-weight:700;color:#f59e0b;margin:20px 0;">' + detail.claimed_by_me + '</div><div style="font-size:14px;color:#666;">已存入你的积分</div>';
    } else if (detail.status === 'empty') {
      bodyHtml = '<div style="font-size:36px;color:#999;margin:20px 0;">已抢完</div>';
    } else if (detail.status === 'expired') {
      bodyHtml = '<div style="font-size:36px;color:#999;margin:20px 0;">已过期</div>';
    } else {
      bodyHtml = '<button id="grp-rp-claim-btn" style="width:180px;height:180px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#fff;font-size:24px;font-weight:700;border:none;cursor:pointer;margin:20px auto;display:block;box-shadow:0 8px 24px rgba(245,158,11,0.3);">開</button>';
    }
    const html = '<div style="text-align:center;padding:30px 20px;">'
      + '<div style="font-size:18px;font-weight:600;margin-bottom:8px;">' + (detail.message || '恭喜发财') + '</div>'
      + '<div style="font-size:13px;color:#999;margin-bottom:20px;">来自 ' + (detail.sender_name || '群友') + ' 的群红包</div>'
      + '<div style="background:linear-gradient(135deg,#fef3c7,#fed7aa);border-radius:16px;padding:30px 20px;margin:0 auto;">'
      + bodyHtml
      + '<div style="font-size:12px;color:#92400e;margin-top:12px;">' + detail.claimed_count + '/' + detail.total_count + ' 已领取 · 总额 ' + detail.total_amount + ' 积分</div>'
      + '</div>'
      + claimsHtml
      + '</div>';
    window.openSubpage('群红包', html);
    setTimeout(() => {
      const btn = document.getElementById('grp-rp-claim-btn');
      if (btn) {
        btn.onclick = async function() {
          btn.disabled = true;
          btn.textContent = '...';
          try {
            const resp = await fetch('/group/red-packets/' + packetId + '/claim', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
            });
            const data = await resp.json();
            if (data.error || data.detail) { alert('领取失败：' + (data.error || data.detail)); btn.disabled = false; btn.textContent = '開'; return; }
            if (window.showGroupToast) window.showGroupToast('🧧 你抢到了 ' + data.amount + ' 积分');
            window.openGroupRedPacket(packetId);
            if (typeof loadGroupMessages === 'function') loadGroupMessages();
          } catch (e) { alert('网络错误：' + e.message); btn.disabled = false; btn.textContent = '開'; }
        };
      }
    }, 100);
  } catch (e) { alert('网络错误：' + e.message); }
};


// 群红包 UI 已迁移到 group_redpacket_ui.js


// ======================================================================
// 【模块 5. 群知识库】
// ======================================================================

// openGroupKnowledge 已迁移到 group_knowledge_ui.js

// openGroupKnowledgeDetail 已迁移到 group_knowledge_ui.js

// openGroupKnowledgeAdd 已迁移到 group_knowledge_ui.js


// ======================================================================
// 【模块 6. 蜂群模式管理】
// ======================================================================

// 蜂群管理 UI 已迁移到 group_swarm_ui.js


// ======================================================================
// 【模块 7. 群管理（公告/管理员/转让）】
// ======================================================================

// 群管理 UI 已迁移到 group_manage_ui.js

window.openGroupAgentPickerForReply = async function(quotedText, groupId) {
  // 决策 1：优先用当前切换的身份
  if (typeof currentAgentId !== 'undefined' && currentAgentId) {
    const source = window.currentAgentSource || 'self';
    await window._generateReplyWithAgent(currentAgentId, source, quotedText, groupId);
    return;
  }

  // 决策 2：没切身份 → 弹选择列表
  let myAgents = [];
  let sharedAgents = [];

  try {
    const mine = await api.listMyAgents();
    myAgents = ((mine && mine.agents) || []).filter(a => !(a.agent_id || '').startsWith('sases_assistant'));
  } catch (e) {}

  try {
    const poolResp = await fetch('/group/' + groupId + '/resource-pool', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const poolData = await poolResp.json();
    sharedAgents = (poolData.pool || []).filter(p => p.enabled);
  } catch (e) {}

  const html = `
    <div class="me-menu" id="reply-agent-list">
      <div class="section-title">我的智能体</div>
      ${myAgents.length === 0 ? '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">无</div>' : ''}
      ${myAgents.map(a => '<div class="me-menu-item reply-agent-option" data-agent-id="' + a.agent_id + '" data-source="self"><span class="menu-label">' + (a.name || a.agent_id) + '</span><span class="menu-arrow">›</span></div>').join('')}
      ${sharedAgents.length > 0 ? '<div class="section-title">群共享智能体</div>' : ''}
      ${sharedAgents.map(p => '<div class="me-menu-item reply-agent-option" data-agent-id="' + p.agent_id + '" data-source="group"><span class="menu-label">' + (p.model_name || p.agent_id) + '</span><span class="menu-value" style="font-size:12px;color:#999;">群共享</span></div>').join('')}
    </div>
  `;

  window.openSubpage('选择智能体生成回复', html, {
    showMore: false,
    returnAction: () => {}
  });

  setTimeout(() => {
    document.querySelectorAll('.reply-agent-option').forEach(el => {
      el.onclick = async () => {
        const agentId = el.dataset.agentId;
        const source = el.dataset.source;
        window.closeSubpage();
        await window._generateReplyWithAgent(agentId, source, quotedText, groupId);
      };
    });
  }, 300);
};


// ======================================================================
// 【模块 9. 群文件】
// ======================================================================

// openGroupFiles 已迁移到 group_file_ui.js，通过 import 使用


// ======================================================================
// 【模块 10. 消息渲染与 WS 增量】
// ======================================================================

async function loadGroupMessages() {
  try {
    const data = await api.getGroupMessages(currentGroupId);
    const messages = data.messages || [];
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    messages.forEach(msg => {
      let isSelf = false;
      if (msg.sender_agent_id) {
        isSelf = currentAgentId != null && String(msg.sender_agent_id) === String(currentAgentId);
      } else {
        isSelf = currentUserId != null && String(msg.sender_id) === String(currentUserId);
      }
      appendGroupMessage(msg.sender_name, msg.content, isSelf, true);
    });
    // 立刻滚 + 多帧滚动（覆盖异步卡片渲染）
    container.scrollTop = container.scrollHeight;
    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
    [100, 300, 500, 800, 1200].forEach(t => {
      setTimeout(() => { container.scrollTop = container.scrollHeight; }, t);
    });
  } catch (e) {
    appendGroupMessage('系统', '加载消息失败：' + e.message, false);
  }
}

function appendGroupMessage(senderName, content, isSelf = false, skipScroll = false) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  const wrapper = document.createElement('div');
  wrapper.className = `message-row ${isSelf ? 'user' : 'assistant'}`;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = (senderName || '?').charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.className = `message ${isSelf ? 'user' : 'assistant'}`;

  let _rendered = false;
  if (typeof content === 'string' && content.startsWith('[IMAGE]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderImageBubble === 'function') {
        const node = m.renderImageBubble(content, isSelf ? 'user' : 'assistant', senderName);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
          if (!skipScroll) messages.scrollTop = messages.scrollHeight;
        }
      }
    });
    _rendered = true;
  } else if (typeof content === 'string' && content.startsWith('[RED_PACKET]:')) {
    let _rp_data = {};
    try { _rp_data = JSON.parse(content.substring(13)); } catch (e) {}
    if (_rp_data.packet_id) {
      // 预占高度，避免卡片异步渲染时页面跳动
      bubble.style.minHeight = '160px';
      bubble.style.width = '220px';
      import('./chat_ui.js').then(m => {
        if (typeof m.renderGroupRedPacketBubble === 'function') {
          const node = m.renderGroupRedPacketBubble(content);
          if (node && node.nodeType) {
            bubble.innerHTML = '';
            bubble.style.padding = '0';
            bubble.style.background = 'transparent';
            bubble.style.border = 'none';
            bubble.appendChild(node);
          }
        }
      });
      _rendered = true;
    }

  } else if (typeof content === 'string' && content.startsWith('[RED_PACKET_DONE]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderRedPacketDoneBubble === 'function') {
        const node = m.renderRedPacketDoneBubble(content);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
          if (!skipScroll) messages.scrollTop = messages.scrollHeight;
        }
      }
    });
    _rendered = true;

  } else if (typeof content === 'string' && content.startsWith('[TASK_CARD]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderTaskCardBubble === 'function') {
        const node = m.renderTaskCardBubble(content);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
          if (!skipScroll) messages.scrollTop = messages.scrollHeight;
        }
      }
    });
    _rendered = true;

  } else if (typeof content === 'string' && content.startsWith('[FILE]:')) {
    import('./chat_ui.js').then(m => {
      if (typeof m.renderFileBubble === 'function') {
        const node = m.renderFileBubble(content, isSelf ? 'user' : 'assistant', senderName);
        if (node && node.nodeType) {
          bubble.innerHTML = '';
          bubble.style.padding = '0';
          bubble.style.background = 'transparent';
          bubble.style.border = 'none';
          bubble.appendChild(node);
          if (!skipScroll) messages.scrollTop = messages.scrollHeight;
        }
      }
    });
    _rendered = true;
  }
  if (!_rendered) {
    if (!isSelf) {
      bubble.innerHTML = `<span class="group-msg-sender">${senderName}:</span> ${content}`;
    } else {
      bubble.textContent = content;
    }
  }
  wrapper.dataset.content = content;
  wrapper.dataset.senderName = senderName || '';
  if (!isSelf && typeof window.attachLongPress === 'function') {
    window.attachLongPress(wrapper, { isGroup: true, groupId: currentGroupId });
  }
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);

  messages.appendChild(wrapper);
  if (!skipScroll) messages.scrollTop = messages.scrollHeight;
  // 高频多帧滚动，覆盖异步渲染的所有时机
  requestAnimationFrame(() => { if (!skipScroll) messages.scrollTop = messages.scrollHeight; });
  [30, 60, 100, 150, 200, 280, 380, 500, 700, 1000].forEach(t => {
    setTimeout(() => { if (!skipScroll) messages.scrollTop = messages.scrollHeight; }, t);
  });
}

// ======================================================================
// 【模块 11. 任务发布与详情】
// ======================================================================

// 群任务 UI 已迁移到 group_task_ui.js


// ======================================================================
// 【模块 12. 发送群消息（乐观渲染）】
// ======================================================================

export async function sendGroupMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  const atts = (window.chatState && Array.isArray(window.chatState.pendingAttachments)) ? [...window.chatState.pendingAttachments] : [];
  if (!text && atts.length === 0) return;
  if (!currentGroupId) return;

  // 乐观渲染：立刻显示用户消息
  if (text) {
    appendGroupMessage('我', text, true);
  }
  input.value = '';
  if (window.chatState) window.chatState.pendingAttachments = [];
  if (window.__sasesClearAttachment) window.__sasesClearAttachment();

  try {
    for (const att of atts) {
      let content = '';
      if (att.type === 'image') {
        const res = await api.uploadImage(att.file);
        if (res && res.url) content = '[IMAGE]:' + res.url;
      } else {
        const res = await api.uploadFile(att.file);
        if (res && res.url) content = '[FILE]:' + res.url + '|' + att.name + '|' + att.size;
      }
      if (content) {
        await api.sendGroupMessage(currentGroupId, content, currentAgentId);
        appendGroupMessage('我', content, true);
      }
    }
    if (text) {
      await api.sendGroupMessage(currentGroupId, text, currentAgentId);
    }
  } catch (e) {
    const _lastMsg = document.querySelector('#chat-messages .message-row.user:last-child .message');
    if (_lastMsg) {
      _lastMsg.style.background = '#ffebee';
      _lastMsg.style.color = '#c62828';
    }
    alert('发送失败：' + (e.message || '未知错误'));
  }
}

// ==================== 群模式切换（下拉菜单） ====================
// ======================================================================
// 【模块 13. 模式切换（普通/蜂群）】
// ======================================================================

async function openGroupModeMenu() {
  const menu = document.getElementById('mode-menu');
  const content = document.getElementById('mode-menu-content');
  if (!menu || !content) return;

  let swarmEnabled = false;
  try {
    const r = await fetch('/group/' + currentGroupId + '/swarm/status', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const d = await r.json();
    swarmEnabled = !!d.swarm_enabled;
  } catch (e) {}

  const normalHtml = '<div class="plus-menu-item mode-item ' + (currentGroupMode === 'normal' ? 'active-mode' : '') + '" data-mode="normal"><span class="plus-menu-label">普通聊天</span></div>';
  const swarmHtml = swarmEnabled ? '<div class="plus-menu-item mode-item ' + (currentGroupMode === 'swarm' ? 'active-mode' : '') + '" data-mode="swarm"><span class="plus-menu-label">蜂群模式</span></div>' : '';
  content.innerHTML = normalHtml + swarmHtml;

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    const rect = modeBtn.getBoundingClientRect();
    content.style.left = rect.left + 'px';
    content.style.top = (rect.bottom + 5) + 'px';
    content.style.position = 'fixed';
  }

  menu.style.display = 'block';
  document.getElementById('mode-menu-overlay').onclick = closeGroupModeMenu;

  content.querySelectorAll('.mode-item').forEach(el => {
    el.addEventListener('click', async () => {
      const mode = el.dataset.mode;
      await applyGroupMode(mode);
      closeGroupModeMenu();
    });
  });
}

function closeGroupModeMenu() {
  document.getElementById('mode-menu').style.display = 'none';
}

async function applyGroupMode(mode) {
  // 保存当前模式下的身份选择
  try {
    localStorage.setItem('sases_agent_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '');
          localStorage.setItem('sases_agent_name_' + currentGroupMode + '_' + currentGroupId, (opt.dataset.agentName || ''));
  } catch (e) {}
  currentGroupMode = mode;
  try {
    localStorage.setItem('sases_group_mode_' + currentGroupId, mode);
  } catch (e) {}
  // 恢复新模式下的身份选择
  try {
    const _saved = localStorage.getItem('sases_agent_' + mode + '_' + currentGroupId) || '';
    currentAgentId = _saved || null;
  } catch (e) {
    currentAgentId = null;
  }
  // 校验当前身份是否合法（蜂群模式下不能选自己的私有智能体）
  if (mode === 'swarm' && currentAgentId) {
    try {
      const _pr = await fetch('/group/' + currentGroupId + '/resource-pool', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const _pd = await _pr.json();
      const _sharedIds = (_pd.pool || []).map(p => p.agent_id);
      if (!_sharedIds.includes(currentAgentId)) {
        currentAgentId = null;
      }
    } catch (e) {
      currentAgentId = null;
    }
  }
  const modeText = document.getElementById('chat-mode-text');
  if (modeText) modeText.textContent = mode === 'normal' ? '普通聊天' : '蜂群模式';
  if (typeof window.showGroupToast === 'function') {
    window.showGroupToast(mode === 'swarm' ? '已切换到蜂群模式' : '已切换到普通模式');
  }
  // 更新 🤖 按钮显示
  try {
    const m = await import('./chat_identity.js');
    if (m && typeof m.updateIdentityButton === 'function') {
      m.updateIdentityButton({ senderAgentId: currentAgentId });
    }
  } catch (e) {}
}

// ======================================================================
// 【模块 14. 群设置主入口】
// ======================================================================

async function openGroupSettings() {
  const contentHtml = `
    <div class="group-settings-container">
      <div class="member-grid" id="group-members-container"><div class="subpage-placeholder">加载中...</div></div>
      <div class="me-menu">
<div class="me-menu-item" id="group-name-entry" style="cursor:pointer;"><span class="menu-label">群聊名称</span><span class="menu-value" id="group-name-value">${currentGroupName}</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="identity-switch-entry"><span class="menu-label">身份切换</span><span class="menu-value" id="identity-current">以本人身份</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-mode-entry"><span class="menu-label">群模式</span><span class="menu-value" id="group-mode-current">${currentGroupMode === 'normal' ? '普通聊天' : '蜂群模式'}</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="announcement-entry"><span class="menu-label">群公告</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="nickname-entry"><span class="menu-label">我在本群的昵称</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="search-history-entry"><span class="menu-label">查找聊天记录</span><span class="menu-arrow">›</span></div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="mute-entry"><span class="menu-label">消息免打扰</span><div class="switch" id="mute-switch"><div class="slider"></div></div></div>
        <div class="me-menu-item" id="pin-entry"><span class="menu-label">置顶聊天</span><div class="switch" id="pin-switch"><div class="slider"></div></div></div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="group-credits-entry"><span class="menu-label">群积分</span><span class="menu-value" id="group-credits-balance">0</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-leaderboard-entry"><span class="menu-label">群排行榜</span><span class="menu-arrow">›</span></div>
      </div>

      <div class="me-menu">
        <div class="me-menu-item" id="group-knowledge-entry"><span class="menu-label">群知识库</span><span class="menu-arrow">›</span></div>

        <div class="me-menu-item" id="swarm-config-entry" style="display:none;"><span class="menu-label">蜂群模式管理</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-manage-entry" style="display:none;"><span class="menu-label">群管理</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-report-entry" style="display:none;"><span class="menu-label">群汇报</span><span class="menu-value" id="group-report-count">0</span><span class="menu-arrow">›</span></div>
        <div class="me-menu-item" id="group-files-entry"><span class="menu-label">群文件</span><span class="menu-arrow">›</span></div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="clear-history-entry"><span class="menu-label">清空聊天记录</span></div>
        <div class="me-menu-item danger" id="leave-group-entry"><span class="menu-label">退出群聊</span></div>
      </div>
    </div>
  `;
  window.openSubpage('群设置', contentHtml, { showMore: false });

  loadGroupCredits();
  await loadGroupMembers();

  const _gnEntry = document.getElementById('group-name-entry');
  if (_gnEntry) _gnEntry.addEventListener('click', openGroupNameEditor);

  const identityEntry = document.getElementById('identity-switch-entry');
  if (identityEntry) identityEntry.addEventListener('click', () => openAgentSwitch(false));

  const groupModeEntry = document.getElementById('group-mode-entry');
  if (groupModeEntry) groupModeEntry.addEventListener('click', openGroupModeMenu);

  const announcementEntry = document.getElementById('announcement-entry');
  if (announcementEntry) announcementEntry.addEventListener('click', openAnnouncementEditor);

  const nicknameEntry = document.getElementById('nickname-entry');
  if (nicknameEntry) nicknameEntry.addEventListener('click', openNicknameEditor);

  const searchHistoryEntry = document.getElementById('search-history-entry');
  if (searchHistoryEntry) searchHistoryEntry.addEventListener('click', openGroupSearch);

  const muteEntry = document.getElementById('mute-entry');
  if (muteEntry) muteEntry.addEventListener('click', toggleGroupMute);

  const pinEntry = document.getElementById('pin-entry');
  if (pinEntry) pinEntry.addEventListener('click', toggleGroupPin);

  const groupCreditsEntry = document.getElementById('group-credits-entry');
  if (groupCreditsEntry) groupCreditsEntry.addEventListener('click', openGroupCreditsDetail);

  const groupLeaderboardEntry = document.getElementById('group-leaderboard-entry');
  if (groupLeaderboardEntry) groupLeaderboardEntry.addEventListener('click', openGroupLeaderboard);

  const clearHistoryEntry = document.getElementById('clear-history-entry');
  if (clearHistoryEntry) clearHistoryEntry.addEventListener('click', clearGroupHistory);

  const leaveGroupEntry = document.getElementById('leave-group-entry');
  if (leaveGroupEntry) leaveGroupEntry.addEventListener('click', leaveGroup);

  // 权限判断：群主/管理员
  let _isOwnerOrAdmin = false;
  let _isOwner = false;
  try {
    const _resp = await fetch('/group/' + currentGroupId + '/admins', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const _data = await _resp.json();
    const _admins = _data.admins || [];
    for (const a of _admins) {
      if (String(a.user_id) === String(currentUserId)) {
        if (a.role === 'owner') {
          _isOwner = true;
          _isOwnerOrAdmin = true;
        } else if (a.role === 'admin') {
          _isOwnerOrAdmin = true;
        }
        break;
      }
    }
  } catch (e) {}

  // 群知识库（所有成员可见）
  const _gkEntry = document.getElementById('group-knowledge-entry');
  if (_gkEntry) {
    _gkEntry.addEventListener('click', () => {
      if (typeof window.openGroupKnowledge === 'function') {
        window.openGroupKnowledge(currentGroupId);
      } else {
        alert('群知识库开发中');
      }
    });
  }

  // 蜂群模式管理（仅群主可见）
  const _scEntry = document.getElementById('swarm-config-entry');
  if (_scEntry) {
    if (_isOwnerOrAdmin) {
      _scEntry.style.display = '';
      _scEntry.addEventListener('click', () => {
        if (typeof window.openSwarmConfig === 'function') {
          window.openSwarmConfig(currentGroupId);
        } else {
          alert('蜂群模式管理开发中');
        }
      });
    } else {
      _scEntry.style.display = 'none';
    }
  }

  // 群管理（群主/管理员可见）
  const _gmEntry = document.getElementById('group-manage-entry');
  if (_gmEntry) {
    if (_isOwnerOrAdmin) {
      _gmEntry.style.display = '';
      _gmEntry.addEventListener('click', () => {
        if (typeof window.openGroupManage === 'function') {
          window.openGroupManage(currentGroupId);
        } else {
          alert('群管理开发中');
        }
      });
    } else {
      _gmEntry.style.display = 'none';
    }
  }

  // 群文件（所有成员可见）
  const _gfEntry = document.getElementById('group-files-entry');
  if (_gfEntry) {
    _gfEntry.addEventListener('click', () => {
      if (typeof window.openGroupFiles === 'function') {
        window.openGroupFiles(currentGroupId);
      } else {
        alert('群文件开发中');
      }
    });
  }

  // 群汇报（群主/管理员可见）
  const _grEntry = document.getElementById('group-report-entry');
  if (_grEntry) {
    if (_isOwnerOrAdmin) {
      _grEntry.style.display = '';
      _grEntry.addEventListener('click', () => {
        if (typeof window.openGroupReportQueue === 'function') {
          window.openGroupReportQueue(currentGroupId);
        } else {
          alert('群汇报开发中');
        }
      });
      fetch('/group/' + currentGroupId + '/report-queue?status=pending', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      }).then(r => r.json()).then(d => {
        const n = (d.items || []).length;
        const cnt = document.getElementById('group-report-count');
        if (cnt) cnt.textContent = n;
      }).catch(() => {});
    } else {
      _grEntry.style.display = 'none';
    }
  }
}

// ======================================================================
// 【模块 15. 群积分加载】
// ======================================================================

async function loadGroupCredits() {
  try {
    const data = await api.getGroupCredits(currentGroupId);
    const credits = data.credits || 0;
    document.getElementById('group-credits-balance').textContent = credits;
  } catch (e) {
    document.getElementById('group-credits-balance').textContent = '0';
  }
}

async function loadGroupMembers() {
  try {
    const data = await api.getGroupMembers(currentGroupId);
    const members = data.members || [];
    const container = document.getElementById('group-members-container');
    let html = '';
    members.forEach(member => {
      const icon = member.member_type === 'agent' ? '🤖' : '👤';
      const displayName = member.display_name || '成员';
      html += `
        <div class="member-grid-item" data-user-id="${member.user_id || ''}" data-agent-id="${member.agent_id || ''}">
          <div class="member-grid-avatar">${icon}</div>
          <div class="member-grid-name">${displayName}</div>
        </div>
      `;
    });
    html += `
      <div class="member-grid-item member-grid-action" id="invite-member-btn"><div class="member-grid-avatar action">＋</div><div class="member-grid-name">邀请</div></div>
      <div class="member-grid-item member-grid-action" id="remove-member-btn"><div class="member-grid-avatar action">－</div><div class="member-grid-name">移除</div></div>
    `;
    container.innerHTML = html;
    const inviteBtn = document.getElementById('invite-member-btn');
    if (inviteBtn) inviteBtn.addEventListener('click', openInviteDialog);
    const removeBtn = document.getElementById('remove-member-btn');
    if (removeBtn) removeBtn.addEventListener('click', openRemoveDialog);
  } catch (e) {
    document.getElementById('group-members-container').innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}

// ======================================================================
// 【模块 16. 邀请/移除成员】
// ======================================================================

function openInviteDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">用户名 / SASES ID / 智能体 ID</span>
        <input type="text" id="invite-input" class="inline-input" placeholder="输入用户名、SASES ID 或智能体 ID">
      </div>
    </div>
    <button class="save-btn" id="confirm-invite-btn">邀请</button>
  `;
  window.openSubpage('邀请成员', contentHtml);

  setTimeout(() => {
    document.getElementById('confirm-invite-btn').addEventListener('click', async () => {
      const input = document.getElementById('invite-input').value.trim();
      if (!input) { alert('请输入用户名或 ID'); return; }
      try {
        await api.inviteToGroup(currentGroupId, input);
        alert('邀请成功');
        window.closeSubpage();
        openGroupSettings();
      } catch (e) {
        alert('邀请失败：' + e.message);
      }
    });
  }, 300);
}

function openRemoveDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">输入要移除的成员 ID 或名称</span>
        <input type="text" id="remove-input" class="inline-input" placeholder="输入用户 ID 或智能体 ID">
      </div>
    </div>
    <button class="save-btn" id="confirm-remove-btn" style="background:#ff3b30;">移除</button>
  `;
  window.openSubpage('移除成员', contentHtml);

  setTimeout(() => {
    document.getElementById('confirm-remove-btn').addEventListener('click', async () => {
      const input = document.getElementById('remove-input').value.trim();
      if (!input) { alert('请输入成员标识'); return; }
      try {
        await api.removeGroupMember(currentGroupId, input);
        alert('移除成功');
        window.closeSubpage();
        openGroupSettings();
      } catch (e) {
        alert('移除失败：' + e.message);
      }
    });
  }, 300);
}

// ======================================================================
// 【模块 17. 身份切换】
// ======================================================================

async function openAgentSwitch(fromChat = false) {
  const contentHtml = `
    <div class="me-menu" id="agent-switch-list">
      <div class="subpage-placeholder">加载中...</div>
    </div>
  `;
  window.openSubpage('选择发言身份', contentHtml, {
    returnAction: fromChat ? null : (() => openGroupSettings())
  });

  try {
    const mine = await api.listMyAgents();
    const myAgents = (mine && mine.agents) || [];

    let sharedAgents = [];
    let swarmEnabled = false;
    try {
      const poolResp = await fetch('/group/' + currentGroupId + '/resource-pool', {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const poolData = await poolResp.json();
      swarmEnabled = !!poolData.swarm_enabled;
      sharedAgents = (poolData.pool || []).filter(p => p.enabled);
    } catch (e) {}

    const container = document.getElementById('agent-switch-list');
    if (!container) return;

    let html = '';
    const isSwarm = currentGroupMode === 'swarm';

    if (!isSwarm) {
      // 普通模式：我的智能体
      html += '<div class="section-title">我的智能体</div>';
      html += '<div class="me-menu">';
      html += '<div class="me-menu-item agent-option" data-agent-id="" data-agent-source="self">以本人身份</div>';
      const _myFiltered = myAgents.filter(a => !(a.agent_id || '').startsWith('sases_assistant'));
      if (_myFiltered.length === 0) {
        html += '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">你还没有智能体</div>';
      } else {
        _myFiltered.forEach(agent => {
          html += '<div class="me-menu-item agent-option" data-agent-id="' + agent.agent_id + '" data-agent-name="' + (agent.name || agent.agent_id) + '" data-agent-source="self">';
          html += '<span class="menu-label">' + (agent.name || agent.agent_id) + '</span>';
          html += '<span class="menu-arrow">›</span>';
          html += '</div>';
        });
      }
      html += '</div>';
    } else {
      // 蜂群模式：以本人身份 + 群共享
      html += '<div class="section-title">群共享智能体</div>';
      html += '<div class="me-menu">';
      html += '<div class="me-menu-item agent-option" data-agent-id="" data-agent-source="self">以本人身份</div>';
      if (sharedAgents.length === 0) {
        html += '<div class="subpage-placeholder" style="padding:20px 0;font-size:13px;">群主未共享智能体</div>';
      } else {
        sharedAgents.forEach(p => {
          html += '<div class="me-menu-item agent-option" data-agent-id="' + p.agent_id + '" data-agent-name="' + (p.model_name || p.agent_id) + '" data-agent-source="group">';
          html += '<span class="menu-label">' + (p.model_name || p.agent_id) + '</span>';
          html += '</div>';
        });
      }
      html += '</div>';
    }

    container.innerHTML = html;

    container.querySelectorAll('.agent-option').forEach(opt => {
      opt.addEventListener('click', () => {
        currentAgentId = opt.dataset.agentId || null;
        window.currentAgentSource = opt.dataset.agentSource || 'self';
        try {
          localStorage.setItem('sases_agent_' + currentGroupMode + '_' + currentGroupId, currentAgentId || '');
        } catch (e) {}
        window.closeSubpage();
        const _name = opt.dataset.agentName || '';
        const _btn = document.getElementById('identity-btn');
        if (_btn) {
          if (currentAgentId) {
            _btn.textContent = (_name || currentAgentId).substring(0, 2);
            _btn.style.background = '#07c160';
            _btn.style.color = '#fff';
            _btn.style.borderRadius = '50%';
            _btn.style.width = '32px';
            _btn.style.height = '32px';
            _btn.style.display = 'flex';
            _btn.style.alignItems = 'center';
            _btn.style.justifyContent = 'center';
            _btn.style.fontSize = '11px';
            _btn.style.fontWeight = '600';
          } else {
            _btn.textContent = '🤖';
            _btn.style.background = 'none';
            _btn.style.color = '';
            _btn.style.borderRadius = '';
            _btn.style.width = '';
            _btn.style.height = '';
            _btn.style.fontSize = '';
          }
        }
        document.getElementById('chat-window-title').textContent = currentGroupName + (currentAgentId ? ' (' + (_name || '智能体') + ')' : '');
      });
    });
  } catch (e) {
    const container = document.getElementById('agent-switch-list');
    if (container) {
      container.innerHTML = '<div class="subpage-placeholder">加载失败：' + e.message + '</div>';
    }
  }
}

// ======================================================================
// 【模块 18. 群公告 + 群名称编辑】
// ======================================================================

window.openAnnouncementEditor = async function() {


window.openGroupNameEditor = function() {
  var canEdit = !!(window.isGroupOwner || window.isGroupAdmin);
  var v = currentGroupName || '';
  var h = document.getElementById('gne-page');
  if (!h) { h = document.createElement('div'); h.id = 'gne-page'; h.className = 'page-secondary'; document.body.appendChild(h); }
  h.innerHTML = '<div class="sp-bar"><span id="gne-back">返回</span><b>群聊名称</b></div><input id="gne-in" value="' + v + '"' + (canEdit ? '' : ' readonly') + '><button id="gne-save"' + (canEdit ? '' : ' style=display:none') + '>保存</button>';
  h.style.display = 'block';
  document.getElementById('gne-back').onclick = function(){ h.style.display = 'none'; };
  document.getElementById('gne-save').onclick = function(){ currentGroupName = document.getElementById('gne-in').value.trim(); h.style.display = 'none'; if (window.renderGroupSettings) window.renderGroupSettings(); };
};

  const groupId = currentGroupId;
  if (!groupId) return;

  // 权限判断
  let isOwnerOrAdmin = false;
  try {
    const resp = await fetch('/group/' + groupId + '/admins', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    for (const a of (data.admins || [])) {
      if (String(a.user_id) === String(currentUserId)) {
        if (a.role === 'owner' || a.role === 'admin') isOwnerOrAdmin = true;
        break;
      }
    }
  } catch (e) {}

  // 读公告
  let content = '';
  try {
    const resp = await fetch('/group/' + groupId + '/announcement', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    content = data.announcement || '';
  } catch (e) {}

  if (isOwnerOrAdmin) {
    const html = `
      <div class="me-menu">
        <div class="me-menu-item" style="display:block;padding:12px;">
          <textarea id="announcement-input" rows="10" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;" placeholder="点击输入群公告，最多 2000 字">${content}</textarea>
        </div>
      </div>
      <button class="save-btn" id="announcement-save">保存</button>
    `;
    window.openSubpage('群公告', html, {
      returnAction: () => openGroupSettings()
    });
    setTimeout(() => {
      const btn = document.getElementById('announcement-save');
      if (!btn) return;
      btn.onclick = async () => {
        const newContent = (document.getElementById('announcement-input') || {}).value || '';
        try {
          const resp = await fetch('/group/' + groupId + '/announcement', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
          });
          const data = await resp.json();
          if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
          alert('已保存');
          window.closeSubpage();
        } catch (e) { alert('网络错误：' + e.message); }
      };
    }, 300);
  } else {
    const html = content
      ? '<div class="me-menu"><div class="me-menu-item" style="display:block;padding:14px;font-size:14px;color:#333;line-height:1.7;white-space:pre-wrap;">' + content + '</div></div>'
      : '<div class="subpage-placeholder">暂无群公告</div>';
    window.openSubpage('群公告', html, {
      returnAction: () => openGroupSettings()
    });
  }
};
// ======================================================================
// 【模块 19. 群积分详情 + 质押 + 红包配置】
// ======================================================================

async function openGroupCreditsDetail() {
  let pool = { available: 0, staked: 0, total: 0, red_packet_hour: 20, red_packet_audience: 'all' };
  try {
    const resp = await fetch('/group/' + currentGroupId + '/pool', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    pool = await resp.json();
  } catch (e) {}
  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #007aff, #00c6ff);">
      <div class="wallet-label">可用积分</div>
      <div class="wallet-balance">${pool.available || 0}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">用于发任务、发红包</div>
    </div>
    <div class="wallet-card" style="background: linear-gradient(135deg, #667eea, #764ba2);">
      <div class="wallet-label">质押总额</div>
      <div class="wallet-balance">${pool.staked || 0}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">锁定期 30 天，到期可提取</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gc-stake-entry">
        <span class="menu-icon">💰</span>
        <span class="menu-label">质押积分</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-icon">📊</span>
        <span class="menu-label">总积分</span>
        <span class="menu-value">${pool.total || 0}</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="gc-redpacket-config">
        <span class="menu-icon">🧧</span>
        <span class="menu-label">红包配置</span>
        <span class="menu-value">${_utcHourToLocal(pool.red_packet_hour != null ? pool.red_packet_hour : 20)}:00</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="section-title">积分说明</div>
    <div style="padding:12px;font-size:13px;color:#666;line-height:1.8;">
      • 任务抽成 5% 进入群池<br>
      • 每日空投按活跃度竞争（10000 分/天）<br>
      • 可用余额满 1000 可发群红包
    </div>
  `;
  window.openSubpage('群积分', contentHtml, { showMore: false, returnAction: () => openGroupSettings() });
  setTimeout(() => {
    const stake = document.getElementById('gc-stake-entry');
    if (stake) stake.onclick = openGroupStakeDialog;
    const config = document.getElementById('gc-redpacket-config');
    if (config) config.onclick = openRedPacketConfig;
  }, 300);
}

function openGroupStakeDialog() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">质押金额（最少 10）</span>
        <input type="number" id="gc-stake-amount" class="inline-input" value="10" min="10">
      </div>
    </div>
    <div style="padding:12px;font-size:12px;color:#666;line-height:1.6;">
      质押积分锁定 30 天，到期后可提取。质押后该群获得空投资格（需总积分≥100）。
    </div>
    <button class="save-btn" id="gc-stake-submit">质押</button>
  `;
  window.openSubpage('质押积分', contentHtml, { returnAction: () => openGroupCreditsDetail() });
  setTimeout(() => {
    const btn = document.getElementById('gc-stake-submit');
    if (!btn) return;
    btn.onclick = async () => {
      const amount = parseFloat(document.getElementById('gc-stake-amount').value);
      if (!amount || amount < 10) { alert('最少质押 10'); return; }
      try {
        const resp = await fetch('/group/' + currentGroupId + '/stake', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount: amount })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('质押失败：' + (data.error || data.detail)); return; }
        alert('质押成功');
        window.closeSubpage();
        openGroupCreditsDetail();
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 300);
}


function _utcHourToLocal(utcH) {
  const o = new Date().getTimezoneOffset();
  return Math.floor((utcH - o / 60 + 24) % 24);
}
function _localHourToUtc(localH) {
  const o = new Date().getTimezoneOffset();
  return Math.floor((localH + o / 60 + 24) % 24);
}

function openRedPacketConfig() {
  const html = `
    <div class='me-menu'>
      <div class='me-menu-item'>
        <span class='menu-label'>发放时间（本地时间）</span>
        <input type='number' id='gc-rp-hour' class='inline-input' value='20' min='0' max='23'>
      </div>
      <div class='me-menu-item'>
        <span class='menu-label'>谁可以抢</span>
        <select id='gc-rp-audience' class='inline-input'>
          <option value='all'>所有群成员</option>
          <option value='stakers'>仅质押成员</option>
        </select>
      </div>
      <div style='padding:8px 12px;font-size:12px;color:#999;'>填本地时间，系统自动按 UTC 存储</div>
    </div>
    <button class='save-btn' id='gc-rp-save'>保存配置</button>
  `;
  window.openSubpage('红包配置', html, { returnAction: () => openGroupCreditsDetail() });
  setTimeout(async () => {
    let uh = 20, au = 'all';
    try {
      const r = await fetch('/group/' + currentGroupId + '/pool', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') } });
      const d = await r.json();
      uh = d.red_packet_hour != null ? d.red_packet_hour : 20;
      au = d.red_packet_audience || 'all';
    } catch (e) {}
    const hi = document.getElementById('gc-rp-hour');
    if (hi) hi.value = _utcHourToLocal(uh);
    const au2 = document.getElementById('gc-rp-audience');
    if (au2) au2.value = au;
    const btn = document.getElementById('gc-rp-save');
    if (!btn) return;
    btn.onclick = async () => {
      const lh = parseInt(document.getElementById('gc-rp-hour').value);
      const aud = document.getElementById('gc-rp-audience').value;
      if (isNaN(lh) || lh < 0 || lh > 23) { alert('小时必须 0-23'); return; }
      const u = _localHourToUtc(lh);
      try {
        const resp = await fetch('/group/' + currentGroupId + '/red-packet/config', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ hour: u, audience: aud })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
        alert('已保存');
        window.closeSubpage();
        openGroupCreditsDetail();
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 300);
}
function sendRedPacketNow() {
  if (!confirm('确定立即发放群红包？群池可用余额将均分给符合受众的成员。')) return;
  fetch('/group/' + currentGroupId + '/red-packet/send', {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
  }).then(r => r.json()).then(data => {
    if (data.error || data.detail) { alert('发放失败：' + (data.error || data.detail)); return; }
    alert('已发放 ' + data.total + ' 积分给 ' + data.recipients + ' 人');
    window.closeSubpage();
    openGroupCreditsDetail();
  }).catch(e => alert('网络错误：' + e.message));
}



// ======================================================================
// 【模块 20. 群排行榜】
// ======================================================================

async function openGroupLeaderboard() {
  const tabs = [
    { key: 'contribution', label: '贡献榜' },
    { key: 'task', label: '任务榜' },
    { key: 'redpacket', label: '红包榜' }
  ];
  let currentType = 'contribution';
  let cache = {};

  const renderList = (items) => {
    if (!items || items.length === 0) {
      return '<div style="text-align:center;color:#999;padding:40px 0;">暂无数据</div>';
    }
    let html = '<div style="padding:8px 12px;">';
    items.forEach((it, idx) => {
      const medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : (idx + 1) + '';
      html += '<div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #f5f5f5;">';
      html += '<div style="width:36px;text-align:center;font-size:' + (idx < 3 ? '20px' : '14px') + ';color:' + (idx < 3 ? '#333' : '#999') + ';">' + medal + '</div>';
      html += '<div style="flex:1;margin-left:12px;font-size:14px;color:#333;">' + (it.username || '匿名') + '</div>';
      html += '<div style="font-size:14px;color:#f59e0b;font-weight:600;">' + (it.score || 0) + '</div>';
      html += '</div>';
    });
    html += '</div>';
    return html;
  };

  const loadData = async (type) => {
    if (cache[type]) return cache[type];
    try {
      const resp = await fetch('/group/' + currentGroupId + '/leaderboard?type=' + type, {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const data = await resp.json();
      cache[type] = data.leaderboard || [];
      return cache[type];
    } catch (e) {
      return [];
    }
  };

  const renderTabs = () => {
    return tabs.map(t =>
      '<div class="lb-tab" data-type="' + t.key + '" style="flex:1;text-align:center;padding:10px 0;font-size:14px;cursor:pointer;">' + t.label + '</div>'
    ).join('');
  };

  const renderPage = async () => {
    const items = await loadData(currentType);
    const contentHtml = `
      <div>
        <div style="display:flex;border-bottom:1px solid #eee;background:#fff;">${renderTabs()}</div>
        <div id="lb-list">${renderList(items)}</div>
      </div>
    `;
    window.openSubpage('群排行榜', contentHtml, { showMore: false, returnAction: () => openGroupSettings() });
    setTimeout(() => {
      document.querySelectorAll('.lb-tab').forEach(el => {
        const t = el.dataset.type;
        const active = t === currentType;
        el.style.color = active ? '#007aff' : '#666';
        el.style.fontWeight = active ? '600' : '400';
        el.style.borderBottom = active ? '2px solid #007aff' : 'none';
        el.onclick = async () => {
          currentType = t;
          const newItems = await loadData(t);
          document.getElementById('lb-list').innerHTML = renderList(newItems);
          document.querySelectorAll('.lb-tab').forEach(e => {
            const tt = e.dataset.type;
            const a = tt === currentType;
            e.style.color = a ? '#007aff' : '#666';
            e.style.fontWeight = a ? '600' : '400';
            e.style.borderBottom = a ? '2px solid #007aff' : 'none';
          });
        };
      });
    }, 100);
  };

  await renderPage();
}
// ======================================================================
// 【模块 21. 群设置基础（昵称/搜索/免打扰/置顶）】
// ======================================================================

function openGroupNameEditor() {
  const html = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">群名称</span>
        <input id="gn-input" type="text" class="inline-input" value="${currentGroupName}" maxlength="50">
      </div>
    </div>
    <button class="save-btn" id="gn-save">保存</button>
  `;
  window.openSubpage('群名称', html, {
    showMore: false,
    returnAction: () => openGroupSettings()
  });
  setTimeout(() => {
    const btn = document.getElementById('gn-save');
    if (!btn) return;
    btn.onclick = () => {
      const newName = (document.getElementById('gn-input') || {}).value || '';
      if (!newName.trim()) { alert('群名不能为空'); return; }
      fetch('/group/' + currentGroupId + '/name', {
        method: 'PATCH',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() })
      }).then(r => r.json()).then(d => {
        if (d.error || d.detail) { alert('保存失败：' + (d.error || d.detail)); return; }
        currentGroupName = newName.trim();
        const el = document.getElementById('group-name-value');
        if (el) el.textContent = currentGroupName;
        document.getElementById('chat-window-title').textContent = currentGroupName;
        alert('已保存');
        window.closeSubpage();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
}

function openNicknameEditor() {
  const html = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">群昵称</span>
        <input id="nick-input" type="text" class="inline-input" maxlength="20" placeholder="最多 20 字">
      </div>
    </div>
    <button class="save-btn" id="nick-save">保存</button>
  `;
  window.openSubpage('我的群昵称', html, {
    showMore: false,
    returnAction: () => openGroupSettings()
  });
  setTimeout(() => {
    const btn = document.getElementById('nick-save');
    if (!btn) return;
    btn.onclick = () => {
      const nn = (document.getElementById('nick-input') || {}).value || '';
      fetch('/group/' + currentGroupId + '/nickname', {
        method: 'PATCH',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: nn })
      }).then(r => r.json()).then(d => {
        if (d.error || d.detail) { alert('保存失败：' + (d.error || d.detail)); return; }
        alert('已保存');
        window.closeSubpage();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
}

function openGroupSearch() {
  const html = `
    <div class="subpage-search-bar">
      <input type="text" id="gs-input" class="search-input" placeholder="输入关键词">
      <button class="search-btn" id="gs-btn">搜索</button>
    </div>
    <div id="gs-results"></div>
  `;
  window.openSubpage('查找聊天记录', html, {
    showMore: false,
    returnAction: () => openGroupSettings()
  });
  setTimeout(() => {
    const input = document.getElementById('gs-input');
    const btn = document.getElementById('gs-btn');
    const doSearch = () => {
      const q = (input || {}).value || '';
      if (!q.trim()) return;
      fetch('/group/' + currentGroupId + '/search-messages?q=' + encodeURIComponent(q), {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      }).then(r => r.json()).then(d => {
        const msgs = d.messages || [];
        const container = document.getElementById('gs-results');
        if (!container) return;
        if (msgs.length === 0) {
          container.innerHTML = '<div class="subpage-placeholder">无匹配结果</div>';
        } else {
          let h = '<div class="me-menu">';
          msgs.forEach(m => {
            h += '<div class="me-menu-item" style="display:block;padding:12px;">';
            h += '<div style="font-size:12px;color:#999;">' + (m.created_at || '') + '</div>';
            h += '<div style="font-size:14px;color:#333;margin-top:4px;white-space:pre-wrap;">' + (m.content || '') + '</div>';
            h += '</div>';
          });
          h += '</div>';
          container.innerHTML = h;
        }
      }).catch(e => alert('网络错误：' + e.message));
    };
    if (btn) btn.onclick = doSearch;
    if (input) input.onkeydown = (e) => { if (e.key === 'Enter') doSearch(); };
  }, 300);
}

function toggleGroupMute() {
  const sw = document.querySelector('#mute-entry .switch');
  const cur = sw && sw.classList.contains('on');
  fetch('/group/' + currentGroupId + '/mute', {
    method: 'PATCH',
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
    body: JSON.stringify({ muted: !cur })
  }).then(r => r.json()).then(d => {
    if (d.error || d.detail) { alert('失败：' + (d.error || d.detail)); return; }
    if (sw) {
      if (d.is_muted) sw.classList.add('on'); else sw.classList.remove('on');
    }
  }).catch(e => alert('网络错误：' + e.message));
}

function toggleGroupPin() {
  const sw = document.querySelector('#pin-entry .switch');
  const cur = sw && sw.classList.contains('on');
  api.togglePinGroup(currentGroupId, !cur).then(() => {
    if (sw) {
      if (!cur) sw.classList.add('on'); else sw.classList.remove('on');
    }
  }).catch(e => alert('操作失败: ' + e.message));
}


// ======================================================================
// 【模块 22. 清空/退出/汇报】
// ======================================================================

function clearGroupHistory() {
  if (!confirm('确定清空本群聊天记录（仅你的视角）？')) return;
  alert('清空功能开发中');
}
function leaveGroup() {
  if (!confirm('确定退出群聊？')) return;
  api.removeGroupMember(currentGroupId, 'self').then(() => { window.closeSubpage(); location.reload(); }).catch(e => alert('失败: ' + e.message));
}

// 群汇报 UI 已迁移到 group_report_ui.js


// window mount
window.openGroupNameEditor = openGroupNameEditor;
window.openNicknameEditor = openNicknameEditor;
window.openGroupSearch = openGroupSearch;
window.toggleGroupMute = toggleGroupMute;
window.toggleGroupPin = toggleGroupPin;
window.openGroupSettings = openGroupSettings;
