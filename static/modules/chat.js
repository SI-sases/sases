import { initParamBar, getParamMaxSteps } from './param_bar.js';
// static/modules/chat.js
import { api } from './api.js';

import { closeGroupChat, sendGroupMessage } from './group_chat.js';
import { appendMessage, createMessageElement, updateMessageStatus } from './chat_ui.js';
import { showWorkWarning, sendWorkCommand, sendCommanderTask, showFreeModeGuide } from './chat_work.js';
import { updateIdentityButton, openIdentitySwitch } from './chat_identity.js';
import { createContextMenu, showQuoteBar, hideQuoteBar, openChatInfo, toggleChatPlusPanel, closeChatPlusPanel } from './chat_menu.js';
import { showProposedRunCard, showTaskDraftEditor, showSwarmActionButtons } from './chat_draft.js';

export const chatState = {
  initialized: false,
  conversationId: null,
  agentId: null,
  agentType: 'my',
  senderAgentId: null,
  mode: 'free',
  voiceMode: false,
  pendingQuote: null,
  lastMessageTime: null,
  offset: 0,
  loadingMore: false,
  hasMore: true
};

window.chatState = chatState;
const PAGE_SIZE = 50;

function handleSend() {
  if (window.currentGroupChat) {
    sendGroupMessage();
    return;
  }

  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  const hasAttach = window.chatState && Array.isArray(window.chatState.pendingAttachments) && window.chatState.pendingAttachments.length > 0;
  if (!text && !hasAttach) return;

  if (chatState.mode === 'free') {
    const execMatch = text.match(/^(?:执行|#1)[：:]\s*(.+)$/);
    if (execMatch) {
      const command = execMatch[1].trim();
      if (!localStorage.getItem('sases_disable_work_warning')) {
        showWorkWarning(command, chatState, api);
        return;
      }
      sendWorkCommand(command, chatState, api);
      return;
    }

    const taskMatch = text.match(/^(?:任务|#2)[：:]\s*(.+)$/);
    if (taskMatch) {
      const taskText = taskMatch[1].trim();
      sendCommanderTask(taskText, chatState, api);
      return;
    }
  }

  sendMessage();
}

async function sendTransfer(receiver_id, amount, message, conversation_id) {
  try {
    const res = await api.transferCredits(receiver_id, amount, message, conversation_id);
    return res;
  } catch (e) {
    console.error('[TRANSFER] sendTransfer failed', e);
    throw e;
  }
}


// ===== 停止按钮（v0.38.0）=====
function _showStopBtn(taskId) {
  if (window.chatState) window.chatState.currentTaskId = taskId;
  const sendBtn = document.getElementById('send-btn');
  const stopBtn = document.getElementById('stop-btn');
  if (sendBtn) sendBtn.style.display = 'none';
  if (stopBtn) stopBtn.style.display = 'block';
  if (window.chatState) {
    if (window.chatState._stopTimer) clearTimeout(window.chatState._stopTimer);
    window.chatState._stopTimer = setTimeout(() => _hideStopBtn(), 30000);
  }
  try { _startPollTimer(taskId); } catch (e) {}
}

async function _pollTaskStatus(taskId) {
  // 轮询任务状态，任务完成后自动隐藏停止按钮
  if (!window.chatState || window.chatState.currentTaskId !== taskId) return;
  try {
    const token = localStorage.getItem('sases_token');
    const r = await fetch('/swarm/reviews?task_id=' + encodeURIComponent(taskId) + '&limit=1', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!r.ok) return;
    const data = await r.json();
    const reviews = data.reviews || [];
    if (!reviews.length) return;
    const last = reviews[0];
    // 任务已完结（pass 或 done）
    if (last && last.review_result && !['retry', 'pending'].includes(last.review_result)) {
      _hideStopBtn();
      // v0.39.1: 任务完成 → 延迟 2 秒显示反馈条（等 AI 回复先落位）
      setTimeout(() => {
        try {
          _renderFeedbackBar(taskId, (window.chatState && window.chatState.conversationId) || null);
        } catch (e) { console.warn('[feedback] 轮询触发失败', e); }
      }, 2000);
    }
  } catch (e) { /* 忽略 */ }
}

function _startPollTimer(taskId) {
  if (window.chatState && window.chatState._pollTimer) {
    clearInterval(window.chatState._pollTimer);
  }
  if (window.chatState) {
    window.chatState._pollTimer = setInterval(() => _pollTaskStatus(taskId), 3000);
  }
}

function _hideStopBtn() {
  if (window.chatState) {
    window.chatState.currentTaskId = null;
    if (window.chatState._stopTimer) {
      clearTimeout(window.chatState._stopTimer);
      window.chatState._stopTimer = null;
    }
  }
  if (window.chatState && window.chatState._pollTimer) {
    clearInterval(window.chatState._pollTimer);
    window.chatState._pollTimer = null;
  }
  const stopBtn = document.getElementById('stop-btn');
  if (stopBtn) stopBtn.style.display = 'none';
  if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
}

function _tryFlushPendingFeedback() {
  // 检查是否该渲染挂起的反馈条
  const st = window.chatState;
  if (!st || !st._pendingFeedback) return;
  const container = document.getElementById('chat-messages');
  if (!container) return;
  // v0.39.4: 消息元素用 data-role 属性标记，不是 class
  const rows = container.querySelectorAll('[data-role]');
  if (!rows.length) return;
  const lastRow = rows[rows.length - 1];
  const _role = lastRow.dataset.role || '';
  // 最后一条是用户消息 → AI 还没回复，不渲染
  if (_role === 'user') return;
  // 渲染
  const { taskId, conversationId } = st._pendingFeedback;
  st._pendingFeedback = null;
  console.log('[feedback] AI 回复落位，渲染反馈条', taskId, '最后消息 role=', _role);
  _renderFeedbackBar(taskId, conversationId);
}

function _renderFeedbackBar(taskId, conversationId) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  // 同任务已有反馈条则不重复
  if (container.querySelector('.feedback-bar[data-task-id="' + taskId + '"]')) return;
  const bar = document.createElement('div');
  bar.className = 'feedback-bar';
  bar.dataset.taskId = taskId;
  bar.innerHTML = '<span class="feedback-label">这次结果满意吗？</span>'
    + '<button class="feedback-btn" data-rating="up">👍</button>'
    + '<button class="feedback-btn" data-rating="down">👎</button>'
    + '<button class="feedback-btn" data-rating="neutral">🤷</button>';

  const _submit = async (rating, reason_tag, reason_text) => {
    bar.querySelectorAll('.feedback-btn').forEach(b => { b.disabled = true; });
    try {
      const token = localStorage.getItem('sases_token');
      const _body = { task_id: taskId, rating, conversation_id: conversationId };
      if (reason_tag) _body.reason_tag = reason_tag;
      if (reason_text) _body.reason_text = reason_text;
      const resp = await fetch('/feedback/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(_body)
      });
      console.log('[feedback] 提交返回', resp.status);
      if (bar.parentNode) {
        bar.innerHTML = '<span class="feedback-done">已记录，谢谢 🙏</span>';
      }
      setTimeout(() => {
        try { if (bar.parentNode) bar.parentNode.removeChild(bar); } catch (e) {}
      }, 3000);
    } catch (e) {
      console.warn('[feedback] 提交失败', e);
      bar.innerHTML = '<span style="color:#ff3b30;">提交失败，请重试</span>';
    }
  };

  const _showReasonPanel = () => {
    // 用二级小条替换主条内容
    bar.innerHTML = '<span class="feedback-label">哪里不满意？</span>'
      + '<button class="feedback-reason-btn" data-rt="understood_wrong">理解错了</button>'
      + '<button class="feedback-reason-btn" data-rt="decomposed_wrong">拆解乱了</button>'
      + '<button class="feedback-reason-btn" data-rt="exec_failed">执行失败</button>'
      + '<button class="feedback-reason-btn" data-rt="output_poor">结果不好看</button>'
      + '<button class="feedback-reason-btn feedback-skip-btn" data-rt="">跳过</button>';
    bar.querySelectorAll('.feedback-reason-btn').forEach(rb => {
      rb.onclick = () => {
        const rt = rb.dataset.rt || null;
        _submit('down', rt, '');
      };
    });
  };

  bar.querySelectorAll('.feedback-btn').forEach(btn => {
    btn.onclick = () => {
      const rating = btn.dataset.rating;
      if (bar._autoRemoveTimer) { clearTimeout(bar._autoRemoveTimer); bar._autoRemoveTimer = null; }
      console.log('[feedback] 点击', rating, 'task_id=', taskId);
      if (rating === 'down') {
        // 弹归因面板
        _showReasonPanel();
      } else {
        _submit(rating, null, '');
      }
    };
  });

  container.appendChild(bar);
  container.scrollTop = container.scrollHeight;
  bar._autoRemoveTimer = setTimeout(() => {
    try {
      if (bar.parentNode) bar.parentNode.removeChild(bar);
      console.log('[feedback] 30 秒未操作，自动移除');
    } catch (e) {}
  }, 30000);
}

async function _stopCurrentTask() {
  const tid = window.chatState && window.chatState.currentTaskId;
  _hideStopBtn();
  if (!tid) return;
  try {
    const token = localStorage.getItem('sases_token');
    await fetch('/swarm/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ task_id: tid })
    });
  } catch (e) { console.warn('[stop] 取消失败', e); }
}

window._renderFeedbackBar = _renderFeedbackBar;
window._showStopBtn = _showStopBtn;
window._hideStopBtn = _hideStopBtn;
window._stopCurrentTask = _stopCurrentTask;

async function sendMessage() {
  const input = document.getElementById('chat-input');

  // 附件：每个独立发一条消息（参考微信）
  if (chatState.pendingAttachments && chatState.pendingAttachments.length) {
    const atts = [...chatState.pendingAttachments];
    chatState.pendingAttachments = [];
    if (typeof window.__sasesClearAttachment === 'function') window.__sasesClearAttachment();
    for (const att of atts) {
      try {
        let content = '';
        if (att.type === 'image') {
          const res = await api.uploadImage(att.file);
          if (res && res.url) content = '[IMAGE]:' + res.url;
        } else {
          const res = await api.uploadFile(att.file);
          if (res && res.url) content = '[FILE]:' + res.url + '|' + att.name + '|' + att.size;
        }
        if (content) {
          appendMessage('user', content, chatState.senderAgentId ? '智能体' : '我', null, new Date().toISOString(), false, chatState);
          await api.sendMessage({
            conversation_id: chatState.conversationId,
            agent_id: chatState.agentId,
            content: content,
            sender_agent_id: chatState.senderAgentId,
            mode: chatState.mode
          });
        }
      } catch (e) {
        alert('上传失败: ' + (e.message || ''));
      }
    }
  }

  let text = input.value.trim();
  if (!text) {
    updateSendButtonVisibility();
    return;
  }

  const tempId = 'temp-' + Date.now();
  appendMessage('user', text, chatState.senderAgentId ? '智能体' : '我', tempId, new Date().toISOString(), true, chatState);
  input.value = '';
  updateSendButtonVisibility();

  try {
    if (chatState.agentType === 'friend' && chatState.agentId) {
      try {
        await api.callAgent(chatState.agentId, text);
      } catch (err) {
        updateMessageStatus(tempId, 'failed');
        return;
      }
    }

    let _maxSteps = null;
    try { _maxSteps = getParamMaxSteps(); } catch (e) {}
    const data = await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: text,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode,
      max_steps: _maxSteps
    });

    if (!chatState.conversationId) {
      chatState.conversationId = data.conversation_id;
    }

    // v0.38.0: 记录写入 HLC，供读己之写检查
    try {
      if (data.write_hlc && data.conversation_id) {
        sessionStorage.setItem('last_write_hlc_' + data.conversation_id, data.write_hlc);
      }
    } catch (e) {}

    updateMessageStatus(tempId, 'sent');
    const _is_swarm_task = !!(data.swarm && data.task_id);
    if (!_is_swarm_task && data.assistant_reply && String(data.assistant_reply).trim() !== String(text).trim()) {
      appendMessage('assistant', data.assistant_reply, 'AI', null, new Date().toISOString(), false, chatState);
    }

    if (data.proposed_run_id) {
      showProposedRunCard(data.proposed_run_id);
    }

    // ========== 草稿模式：渲染可编辑任务编辑器 ==========
    if (data.swarm && data.swarm_status === 'draft' && data.task_id) {
      const steps = data.steps || [];
      showTaskDraftEditor(data.task_id, steps);
    }
    // ========== 普通蜂群任务：显示操作按钮 ==========
    else if (data.swarm && data.task_id) {
      showSwarmActionButtons(data.task_id, text, data.swarm_status);
      _showStopBtn(data.task_id);
    }

    if (typeof window.onboarding?.report === 'function') {
      window.onboarding.report('send_message');
    }
  } catch (err) {
    updateMessageStatus(tempId, 'failed');
  }
}

// ========== 草稿任务编辑器 ==========
function handleBack() {
  if (window.currentGroupChat) {
    closeGroupChat();
    window.currentGroupChat = false;
  } else {
    closeChatWindow();
  }
}

function updateSendButtonVisibility() {
  const input=document.getElementById('chat-input');
  const sendBtn=document.getElementById('send-btn');
  const plusBtn=document.getElementById('input-plus-btn');
  if(!input||!sendBtn||!plusBtn) return;
  const hasText=input.value.trim().length>0;
  const hasAttach=window.chatState&&Array.isArray(window.chatState.pendingAttachments)&&window.chatState.pendingAttachments.length>0;
  if(hasText||hasAttach){sendBtn.style.display='block';plusBtn.style.display='none';}
  else{sendBtn.style.display='none';plusBtn.style.display='block';}
}

window.updateSendButtonVisibility = updateSendButtonVisibility;
window.sendMessage = sendMessage;

window.__sasesClearAttachment = function() {
  if (window.chatState) window.chatState.pendingAttachments = [];
  const el = document.getElementById('attachment-preview');
  if (el) { el.style.display = 'none'; el.innerHTML = ''; }
  if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
};

window.__sasesUploadFile = async (file) => {
  if (!file) return;
  if (!chatState.conversationId) {
    alert('请先进入会话');
    return;
  }
  try {
    const res = await api.uploadFile(file);
    if (!res || !res.url) {
      alert('上传失败');
      return;
    }
    const _content = '[FILE]:' + res.url + '|' + (file.name || 'file') + '|' + (file.size || 0);
    appendMessage('user', _content, chatState.senderAgentId ? '智能体' : '我', null, new Date().toISOString(), false, chatState);
    await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: _content,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode
    });
  } catch (e) {
    alert('上传失败：' + (e.message || '未知错误'));
  }
};

window.__sasesUploadImage = async (file) => {
  if (!file) return;
  if (!chatState.conversationId) {
    alert('请先进入会话');
    return;
  }
  try {
    const res = await api.uploadImage(file);
    if (!res || !res.url) {
      alert('上传失败');
      return;
    }
    await api.sendMessage({
      conversation_id: chatState.conversationId,
      agent_id: chatState.agentId,
      content: '[IMAGE]:' + res.url,
      sender_agent_id: chatState.senderAgentId,
      mode: chatState.mode
    });
    await loadMessages(chatState.conversationId);
  } catch (e) {
    alert('上传失败：' + (e.message || '未知错误'));
  }
};

function toggleVoiceMode() {
  const input = document.getElementById('chat-input');
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (!input || !toggleBtn) return;

  chatState.voiceMode = !chatState.voiceMode;
  if (chatState.voiceMode) {
    input.style.display = 'none';
    toggleBtn.textContent = '⌨️';
    input.placeholder = '按住说话（模拟）';
  } else {
    input.style.display = 'block';
    toggleBtn.textContent = '🎤';
    updateInputPlaceholder();
  }
}

function updateInputPlaceholder() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  if (chatState.mode === 'normal') {
    input.placeholder = '输入消息...';
  } else if (chatState.mode === 'free') {
    input.placeholder = '聊天、执行：命令 或 任务：描述';
  } else {
    input.placeholder = '输入消息...';
  }
}

export function openChatWindow(conversationId, chatName, agentId = null, agentType = 'my', isFriendChat = 0, friendMode = 'normal') {

  // 好友模式切换按钮（模拟）
  if (chatState && chatState.is_friend_chat == 1) {
    var bar = document.createElement('div');
    bar.className = 'friend-mode-bar';
    bar.innerHTML = '<button onclick="alert(\'好友模式切换（模拟）\')">切换好友模式</button>';
    var host = document.getElementById('chat-header') || document.body;
    host.insertBefore(bar, host.firstChild);
  }

  chatState.conversationId = conversationId ? parseInt(conversationId) : null;
  chatState.agentId = agentId;
  chatState.agentType = agentType;
  chatState.senderAgentId = localStorage.getItem('sases_sender_agent_id') || null;
  chatState.mode = 'free';
  chatState.pendingQuote = null;
  chatState.lastMessageTime = null;
  chatState.offset = 0;
  chatState.loadingMore = false;
  chatState.hasMore = true;

  updateModeText();
  updateInputPlaceholder();
  updateIdentityButton(chatState);
  try { initParamBar(); } catch (e) { console.warn('[chat] param_bar 初始化失败', e); }

  const titleEl = document.getElementById('chat-window-title');
  // ====== 好友模式按钮 ======
  const topBar = document.querySelector('.top-actions') || document.querySelector('.top-bar');
  const oldBtn = document.getElementById('friend-mode-btn');
  if (oldBtn) oldBtn.remove();
  if (isFriendChat === 1 && topBar) {
    const btn = document.createElement('button');
    btn.id = 'friend-mode-btn';
    btn.style.cssText = 'margin-right: 8px; padding: 4px 8px; font-size: 12px; border-radius: 4px; border: none; color: #fff; cursor: pointer; background: ' + (friendMode === 'free' ? '#ff9500' : '#007aff') + ';';
    btn.textContent = friendMode === 'free' ? '⚡ 自由模式' : '💬 普通模式';
    btn.onclick = () => {
      alert('当前模式: ' + friendMode + '，点击切换功能待实现');
    };
    topBar.insertBefore(btn, topBar.firstChild);
  }

  if (titleEl) titleEl.textContent = chatName || '会话';

  document.getElementById('view-chat-window').style.display = 'flex';
  document.querySelector('.bottom-nav').style.display = 'none';
  document.querySelector('.top-bar').style.display = 'none';

  const infoBtn = document.getElementById('chat-info-btn');
  const groupSettingsBtn = document.getElementById('group-settings-btn');
  const modeBtn = document.getElementById('chat-mode-btn');
  if (infoBtn) infoBtn.style.display = window.currentGroupChat ? 'none' : 'block';
  if (groupSettingsBtn) groupSettingsBtn.style.display = window.currentGroupChat ? 'block' : 'none';
  if (modeBtn) {
    modeBtn.style.display = 'block';
    modeBtn.onclick = openModeMenu;
  }

  const input = document.getElementById('chat-input');
  if (input) {
    input.style.display = 'block';
    input.value = '';
    if (!input._sasesPasteBound) {
      input._sasesPasteBound = true;
      input.addEventListener('paste', (e) => {
        const items = e.clipboardData && e.clipboardData.items;
        if (!items) return;
        let hasFile = false;
        for (const item of items) {
          if (item.kind === 'file') {
            const f = item.getAsFile();
            if (f && f.type && f.type.indexOf('image/') === 0) {
              hasFile = true;
              window.chatState = window.chatState || {};
              window.chatState.pendingAttachments = window.chatState.pendingAttachments || [];
              window.chatState.pendingAttachments.push({ type: 'image', file: f, name: f.name || ('paste-' + Date.now() + '.png'), size: f.size });
            }
          }
        }
        if (hasFile) {
          e.preventDefault();
          import('./chat_ui.js').then(m => m.renderAttachmentPreview(window.chatState.pendingAttachments));
        }
      });
    }
  }
  const toggleBtn = document.getElementById('toggle-voice-btn');
  if (toggleBtn) toggleBtn.textContent = '🎤';
  chatState.voiceMode = false;

  updateSendButtonVisibility();
  hideQuoteBar();
  closeChatPlusPanel();
  const _stopBtn = document.getElementById('stop-btn');
  if (_stopBtn && !_stopBtn._sasesStopBound) {
    _stopBtn._sasesStopBound = true;
    _stopBtn.onclick = _stopCurrentTask;
  }
  _hideStopBtn();

  const messagesContainer = document.getElementById('chat-messages');
  if (messagesContainer) {
    messagesContainer.innerHTML = '';
    if (!localStorage.getItem('sases_free_mode_guide_dismissed')) {
      const _agentId = chatState.agentId || '';
      const _isSases = _agentId.startsWith('sases_assistant');
      showFreeModeGuide(messagesContainer, _isSases);
    }
  }

  if (chatState.conversationId) {
    loadMessages(chatState.conversationId);
  } else if (chatState.agentId) {
    const _targetAgentId = chatState.agentId;
    api.listConversations().then(_res => {
      if (chatState.agentId !== _targetAgentId) return;
      if (chatState.conversationId) return;
      const _list = (_res && _res.conversations) || [];
      const _existing = _list.find(c => c.agent_id === _targetAgentId);
      if (_existing && _existing.id) {
        chatState.conversationId = parseInt(_existing.id);
        console.log('[chat] 复用已有会话', chatState.conversationId);
        loadMessages(chatState.conversationId);
      }
    }).catch(e => { console.warn('[chat] 查已有会话失败', e); });
  }
}

export function closeChatWindow() {
  chatState.conversationId = null;
  chatState.agentId = null;
  chatState.agentType = 'my';
  chatState.senderAgentId = null;
  chatState.mode = 'free';
  chatState.pendingQuote = null;
  chatState.lastMessageTime = null;
  chatState.offset = 0;
  chatState.loadingMore = false;
  chatState.hasMore = true;

  document.getElementById('view-chat-window').style.display = 'none';
  document.querySelector('.bottom-nav').style.display = 'flex';
  document.querySelector('.top-bar').style.display = 'flex';
  const infoBtn = document.getElementById('chat-info-btn');
  if (infoBtn) infoBtn.style.display = 'none';
  const groupSettingsBtn = document.getElementById('group-settings-btn');
  if (groupSettingsBtn) groupSettingsBtn.style.display = 'none';
  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) modeBtn.style.display = 'none';
  hideQuoteBar();
  closeChatPlusPanel();
  _hideStopBtn();
}

function updateModeText() {
  const modeTextEl = document.getElementById('chat-mode-text');
  if (!modeTextEl) return;
  const modeMap = {
    'free': '自由模式',
    'normal': '普通模式'
  };
  modeTextEl.textContent = modeMap[chatState.mode] || chatState.mode;
}

function openModeMenu() {
  const menu = document.getElementById('mode-menu');
  const content = document.getElementById('mode-menu-content');
  if (!menu || !content) return;

  content.innerHTML = `
    <div class="plus-menu-item mode-item ${chatState.mode === 'normal' ? 'active-mode' : ''}" data-mode="normal">
      <span class="plus-menu-label">普通模式</span>
      <span class="plus-menu-desc" style="font-size:12px;color:#888;">纯聊天，不触发任何功能</span>
    </div>
    <div class="plus-menu-item mode-item ${chatState.mode === 'free' ? 'active-mode' : ''}" data-mode="free">
      <span class="plus-menu-label">自由模式</span>
      <span class="plus-menu-desc" style="font-size:12px;color:#888;">可执行指令、任务协作、分析图片</span>
    </div>
  `;

  const modeBtn = document.getElementById('chat-mode-btn');
  if (modeBtn) {
    const rect = modeBtn.getBoundingClientRect();
    content.style.left = rect.left + 'px';
    content.style.top = (rect.bottom + 5) + 'px';
    content.style.position = 'fixed';
  }

  menu.style.display = 'block';
  document.getElementById('mode-menu-overlay').onclick = closeModeMenu;

  content.querySelectorAll('.mode-item').forEach(el => {
    el.addEventListener('click', () => {
      chatState.mode = el.dataset.mode;
      updateModeText();
      updateInputPlaceholder();
      closeModeMenu();
    });
  });
}

function closeModeMenu() {
  document.getElementById('mode-menu').style.display = 'none';
}

async function loadMessages(conversationId, force = false) {
  chatState.offset = 0;
  chatState.hasMore = true;
  const container = document.getElementById('chat-messages');
  if (!container) return;
  // 检查是否有新消息：无新消息则跳过重建
  try {
    const _check = await api.getConversationMessages(conversationId, 1, 0);
    const _latest = (_check.messages && _check.messages[0]) ? _check.messages[0].id : null;
    if (!force && _latest && _latest === chatState._lastMsgId) {
      return;
    }
    chatState._lastMsgId = _latest;
  } catch (e) { /* 检查失败则继续走原逻辑 */ }
  container.style.visibility = 'hidden';
  container.innerHTML = '';
  try {
    const data = await api.getConversationMessages(conversationId, PAGE_SIZE, 0);
    const messages = data.messages || [];
    if (messages.length < PAGE_SIZE) {
      chatState.hasMore = false;
    }

    // v0.38.0: 读己之写检查 —— 本地最新消息 HLC 落后于写入 HLC 时自动重载一次
    try {
      const _lastWrite = sessionStorage.getItem('last_write_hlc_' + conversationId);
      if (_lastWrite && messages.length > 0) {
        const _latest = messages[messages.length - 1];
        const _latestHlc = _latest && _latest.hlc_ts;
        if (_latestHlc && _latestHlc < _lastWrite && !chatState._rywRetried) {
          chatState._rywRetried = true;
          console.warn('[读己之写] 最新消息 HLC 落后于本地写入，1 秒后重载');
          setTimeout(() => {
            chatState._rywRetried = false;
            loadMessages(conversationId, true);
          }, 1000);
          return;
        }
        // 已追上，清除标记
        chatState._rywRetried = false;
      }
    } catch (e) {}
    
    chatState._bulkLoading = true;
    chatState._seenMsgIds = new Set();
    messages.forEach(msg => {
      if (msg.id) chatState._seenMsgIds.add(msg.id);
      appendMessage(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at, false, chatState);
    });
    chatState._bulkLoading = false;
    chatState.offset = messages.length;
    container.scrollTop = container.scrollHeight;
    const _imgs = container.querySelectorAll('img');
    const _scrollBottom = () => { container.scrollTop = container.scrollHeight; };
    const _done = () => {
      _scrollBottom();
      requestAnimationFrame(_scrollBottom);
      setTimeout(_scrollBottom, 50);
      setTimeout(_scrollBottom, 200);
      container.style.visibility = 'visible';
    };
    if (_imgs.length === 0) {
      requestAnimationFrame(_done);
    } else {
      let _pending = _imgs.length;
      const _tick = () => { if (--_pending <= 0) _done(); };
      _imgs.forEach(img => { if (img.complete) _tick(); else { img.addEventListener('load', _tick); img.addEventListener('error', _tick); } });
      setTimeout(_done, 400);
    }
  } catch (err) {
    container.style.visibility = 'visible';
    appendMessage('assistant', `加载历史消息失败：${err.message}`, 'AI', null, new Date().toISOString(), false, chatState);
  }
}

async function handleScroll() {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  if (container.scrollTop <= 30 && chatState.hasMore && !chatState.loadingMore && chatState.conversationId) {
    chatState.loadingMore = true;
    try {
      const data = await api.getConversationMessages(chatState.conversationId, PAGE_SIZE, chatState.offset);
      const olderMessages = data.messages || [];
      if (olderMessages.length < PAGE_SIZE) {
        chatState.hasMore = false;
      }
      if (olderMessages.length > 0) {
        const prevScrollHeight = container.scrollHeight;
        for (let i = olderMessages.length - 1; i >= 0; i--) {
          const msg = olderMessages[i];
          const wrapper = createMessageElement(msg.sender, msg.content, msg.sender_name, msg.id, msg.created_at, false, true, chatState, msg.msg_type, msg.attachments);
          container.insertBefore(wrapper, container.firstChild);
        }
        container.scrollTop = container.scrollHeight - prevScrollHeight;
      }
      chatState.offset += olderMessages.length;
    } catch (e) {
      console.error('加载更多消息失败', e);
    } finally {
      chatState.loadingMore = false;
    }
  }
}

window.addEventListener('sases_new_message', (e) => {
  const d = e.detail || {};
  // 忽略用户自己发的消息（本地已渲染）
  if (d.sender === 'user') return;
  const _cid = d.conversation_id;
  if (_cid && chatState.conversationId && String(_cid) !== String(chatState.conversationId)) return;
  // 收到最终结果（非协议消息）时，自动移除任务按钮卡片
  const _content_ws = (d.content || '').trim();
  if (_content_ws) {
    document.querySelectorAll('[id^="swarm-actions-"]').forEach(el => el.remove());
  }
  const _content = (d.content || '').trim();
  if (!_content) return;
  const _proto = ['[TASK]:', '[STEP_DONE]:', '[RETRY_TASK]:', '[TASK_DRAFT]:', '[SUPERVISOR_PROGRESS]:'];
  if (_proto.some(p => _content.startsWith(p))) return;
  // 去重
  if (d.message_id) {
    if (!chatState._seenMsgIds) chatState._seenMsgIds = new Set();
    if (chatState._seenMsgIds.has(d.message_id)) return;
    chatState._seenMsgIds.add(d.message_id);
  }
  let _display = _content;
  if (_display.startsWith('[SUMMARY]:')) {
    _display = _display.slice(10);
    const _fbTid = (window.chatState && window.chatState.currentTaskId) || null;
    try { _hideStopBtn(); } catch (e) {}
    if (_fbTid) {
      setTimeout(() => {
        try { _renderFeedbackBar(_fbTid, window.chatState && window.chatState.conversationId); } catch (e) {}
      }, 300);
    }
  }
  if (typeof appendMessage === 'function') {
    appendMessage(d.sender || 'assistant', _display, d.sender_agent_id || 'AI', d.message_id, d.created_at, false, chatState);
  }
});

export function initChat() {
  const sendBtn = document.getElementById('send-btn');
  const input = document.getElementById('chat-input');
  const backBtn = document.getElementById('chat-back-btn');
  const infoBtn = document.getElementById('chat-info-btn');
  const modeBtn = document.getElementById('chat-mode-btn');
  const toggleVoiceBtn = document.getElementById('toggle-voice-btn');
  const identityBtn = document.getElementById('identity-btn');
  const inputPlusBtn = document.getElementById('input-plus-btn');
  const messagesContainer = document.getElementById('chat-messages');

  if (!sendBtn || !input || !backBtn || !infoBtn || !modeBtn || chatState.initialized) return;
  chatState.initialized = true;

  sendBtn.addEventListener('click', handleSend);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  input.addEventListener('input', updateSendButtonVisibility);

  backBtn.addEventListener('click', handleBack);
  infoBtn.addEventListener('click', () => openChatInfo(chatState));
  toggleVoiceBtn.addEventListener('click', toggleVoiceMode);
  identityBtn.addEventListener('click', () => openIdentitySwitch(chatState, api));
  inputPlusBtn.onclick = toggleChatPlusPanel;

  if (messagesContainer) {
    messagesContainer.addEventListener('scroll', handleScroll);
    // v0.39.3: 监听消息区变化，自动 flush 挂起的反馈条
    if (!messagesContainer._sasesFeedbackObserver) {
      const _obs = new MutationObserver(() => {
        try { _tryFlushPendingFeedback(); } catch (e) {}
      });
      _obs.observe(messagesContainer, { childList: true });
      messagesContainer._sasesFeedbackObserver = _obs;
    }
  }

  updateSendButtonVisibility();
  updateIdentityButton(chatState);
  createContextMenu();
}