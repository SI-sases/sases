// static/modules/chat_ui.js

// ========== 协议消息过滤（v0.17.0） ==========
const HIDDEN_PREFIXES = ['[TASK]:', '[TASK_DRAFT]:', '[STEP_DONE]:', '[RETRY_TASK]:', '[SUPERVISOR_PROGRESS]:'];

export function isProtocolMessage(content) {
  if (typeof content !== 'string') return false;
  for (const p of HIDDEN_PREFIXES) {
    if (content.startsWith(p)) return true;
  }
  return false;
}

export function stripSummaryPrefix(content) {
  if (typeof content === 'string' && content.startsWith('[SUMMARY]:')) {
    return content.substring('[SUMMARY]:'.length);
  }
  return content;
}


// ========== HTML 转义 ==========
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ========== 指令消息渲染 ==========
export function appendWorkMessage(role, content, senderName = null) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'row';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.margin = '8px 12px';
  if (role === 'user') {
    wrapper.style.justifyContent = 'flex-end';
  } else {
    wrapper.style.justifyContent = 'flex-start';
  }

  const avatar = document.createElement('div');
  avatar.style.width = '36px';
  avatar.style.height = '36px';
  avatar.style.borderRadius = '50%';
  avatar.style.background = role === 'user' ? '#007aff' : '#e0e0e0';
  avatar.style.color = role === 'user' ? '#fff' : '#333';
  avatar.style.display = 'flex';
  avatar.style.alignItems = 'center';
  avatar.style.justifyContent = 'center';
  avatar.style.flexShrink = '0';
  avatar.style.fontSize = '16px';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.style.maxWidth = '70%';
  bubble.style.padding = '10px 14px';
  bubble.style.borderRadius = role === 'user' ? '12px 2px 12px 12px' : '2px 12px 12px 12px';
  bubble.style.wordBreak = 'break-word';
  bubble.style.whiteSpace = 'pre-wrap';
  bubble.style.fontSize = '15px';
  if (role === 'user') {
    bubble.style.background = '#007aff';
    bubble.style.color = '#fff';
    bubble.innerHTML = `<div style="font-weight:600;">💻 ${escapeHtml(content)}</div>`;
  } else {
    bubble.style.background = '#f0f0f0';
    bubble.style.color = '#333';
    bubble.innerHTML = `<div style="font-weight:600; margin-bottom:6px;">📋 执行结果</div><pre style="margin:0; white-space:pre-wrap; word-break:break-word;">${escapeHtml(content)}</pre>`;
  }

  if (role === 'user') {
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// ========== 普通消息元素创建 ==========
export function createMessageElement(role, content, senderName, messageId, timeIso, isPending = false, skipTimeTag = false, chatState = null, msg_type = 'standard', attachments = null) {
  if (isProtocolMessage(content)) {
    const empty = document.createElement('div');
    empty.style.display = 'none';
    return empty;
  }
  content = stripSummaryPrefix(content);
  if (typeof content === 'string' && content.startsWith('[SUPERVISOR_PROGRESS]:')) {
    const _pd = document.createElement('div');
    _pd.style.cssText = 'text-align:center;font-size:12px;color:#888;margin:6px 12px;';
    _pd.textContent = content.substring(22);
    return _pd;
  }
  if (typeof content === 'string' && content.startsWith('[SUPERVISOR_PROGRESS]:')) {
    const _pd = document.createElement('div');
    _pd.style.cssText = 'text-align:center;font-size:12px;color:#888;margin:6px 12px;';
    _pd.textContent = content.substring(22);
    return _pd;
  }
    // 多模态新增分支
    if (msg_type === 'image' && attachments && attachments.length > 0) {
        return renderImageBubble(`[IMAGE]:${attachments[0].url}`, role, senderName);
    }
    if (msg_type === 'file' && attachments && attachments.length > 0) {
        return renderFileBubble(`[FILE]:${attachments[0].name}|${attachments[0].size || 0}|${attachments[0].url}`, role, senderName);
    }
    if (typeof content === 'string' && content.startsWith('[RED_PACKET]:')) { return renderRedPacketBubble(content); }
  if (typeof content === 'string' && content.startsWith('[IMAGE]:')) { return renderImageBubble(content, role, senderName); }
  if (typeof content === 'string' && content.startsWith('[FILE]:')) { return renderFileBubble(content, role, senderName); }
  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'row';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.margin = '8px 12px';
  wrapper.dataset.messageId = messageId || '';
  wrapper.dataset.role = role;
  wrapper.dataset.senderName = senderName || (role === 'user' ? '我' : 'AI');
  wrapper.dataset.content = content;

  if (role === 'user') {
    wrapper.style.justifyContent = 'flex-end';
  } else {
    wrapper.style.justifyContent = 'flex-start';
  }

  const avatar = document.createElement('div');
  avatar.style.width = '36px';
  avatar.style.height = '36px';
  avatar.style.borderRadius = '50%';
  avatar.style.background = role === 'user' ? '#007aff' : '#e0e0e0';
  avatar.style.color = role === 'user' ? '#fff' : '#333';
  avatar.style.display = 'flex';
  avatar.style.alignItems = 'center';
  avatar.style.justifyContent = 'center';
  avatar.style.flexShrink = '0';
  avatar.style.fontSize = '16px';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();

  const bubble = document.createElement('div');
  bubble.style.maxWidth = '70%';
  bubble.style.padding = '10px 14px';
  bubble.style.borderRadius = role === 'user' ? '12px 2px 12px 12px' : '2px 12px 12px 12px';
  bubble.style.wordBreak = 'break-word';
  bubble.style.whiteSpace = 'pre-wrap';
  bubble.style.fontSize = '15px';
  if (role === 'user') {
    bubble.style.background = '#007aff';
    bubble.style.color = '#fff';
  } else {
    bubble.style.background = '#f0f0f0';
    bubble.style.color = '#333';
  }

  if (role === 'user' && senderName && senderName !== '我') {
    bubble.innerHTML = `<span style="font-weight:600;">${escapeHtml(senderName)}:</span> ${escapeHtml(content)}`;
  } else {
    bubble.textContent = content;
  }

  if (role === 'user') {
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
    if (isPending) {
      const status = document.createElement('span');
      status.className = 'message-status';
      status.style.fontSize = '12px';
      status.style.color = '#999';
      status.style.alignSelf = 'center';
      status.style.marginRight = '8px';
      status.textContent = '发送中...';
      wrapper.appendChild(status);
    }
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  }

  return wrapper;
}

// ========== 消息插入与时间标签 ==========
export function appendMessage(role, content, senderName = null, messageId = null, timeIso = null, isPending = false, chatState = null) {
  if (typeof role !== 'string' || !role) return null;
  if (typeof content !== 'string' || !content) return null;
  if (isProtocolMessage(content)) return null;
  content = stripSummaryPrefix(content);
  if (isProtocolMessage(content)) return;
  const messages = document.getElementById('chat-messages');
  if (!messages) return;

  if (timeIso && chatState) {
    insertTimeTag(timeIso, chatState);
  }

  const wrapper = createMessageElement(role, content, senderName, messageId, timeIso, isPending, false, chatState);
  messages.appendChild(wrapper);
  if (!chatState || !chatState._bulkLoading) messages.scrollTop = messages.scrollHeight;

  if ((role === 'assistant' || role === 'friend') && typeof window.attachLongPress === 'function') {
    window.attachLongPress(wrapper, chatState);
  if (wrapper && wrapper.querySelector && wrapper.querySelector('.red-packet-bubble')) {
    const bubble = wrapper.querySelector('.red-packet-bubble');
    bubble.addEventListener('click', async () => {
      const tx = bubble.dataset.redPacketTx;
      if (!tx) return;
      if (!confirm('确定领取这个红包？')) return;
      try {
        await api.claimRedPacket(parseInt(tx));
        alert('领取成功');
      } catch (e) {
        alert('领取失败：' + (e.message || '未知错误'));
      }
    });
  }
  }
}


export function insertTimeTag(timeIso, chatState) {
  const container = document.getElementById('chat-messages');
  if (!container || !chatState) return;
  if (!chatState.lastMessageTime) {
    chatState.lastMessageTime = timeIso;
    return;
  }
  const diff = new Date(timeIso) - new Date(chatState.lastMessageTime);
  if (Math.abs(diff) > 5 * 60 * 1000) {
    const tag = document.createElement('div');
    tag.style.textAlign = 'center';
    tag.style.fontSize = '12px';
    tag.style.color = '#999';
    tag.style.margin = '8px 0';
    tag.textContent = formatTime(timeIso);
    container.appendChild(tag);
  }
  chatState.lastMessageTime = timeIso;
}

export function formatTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } else if (date.getFullYear() === now.getFullYear()) {
    return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' }) + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } else {
    return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }) + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
}

// ========== 消息状态更新 ==========
export function showImagePreview(url) {
  const overlay = document.createElement('div');
  overlay.style.position = 'fixed';
  overlay.style.top = '0';
  overlay.style.left = '0';
  overlay.style.width = '100vw';
  overlay.style.height = '100vh';
  overlay.style.background = 'rgba(0,0,0,0.85)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.zIndex = '9999';
  overlay.style.cursor = 'zoom-out';
  const img = document.createElement('img');
  img.src = url;
  img.style.maxWidth = '90vw';
  img.style.maxHeight = '90vh';
  img.style.borderRadius = '8px';
  img.style.boxShadow = '0 0 30px rgba(0,0,0,0.6)';
  overlay.appendChild(img);
  const close = () => {
    if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    document.removeEventListener('keydown', escHandler);
  };
  const escHandler = (e) => { if (e.key === 'Escape') close(); };
  overlay.onclick = close;
  document.addEventListener('keydown', escHandler);
  document.body.appendChild(overlay);
}


export function renderFileBubble(content, role, senderName) {
  const parts = (content || '').substring(7).split('|');
  const url = parts[0] || '';
  const name = parts[1] || 'file';
  const size = parseInt(parts[2] || '0', 10);
  const sz = size > 1048576 ? (size/1048576).toFixed(2) + 'MB' : (size > 1024 ? (size/1024).toFixed(1) + 'KB' : size + 'B');
  const w = document.createElement('div');
  w.style.margin = '8px 12px';
  w.style.display = 'flex';
  w.style.justifyContent = role === 'user' ? 'flex-end' : 'flex-start';
  const a = document.createElement('a');
  a.href = url;
  a.target = '_blank';
  a.style.padding = '10px 14px';
  a.style.background = role === 'user' ? '#007aff' : '#f0f0f0';
  a.style.color = role === 'user' ? '#fff' : '#333';
  a.style.borderRadius = '8px';
  a.style.textDecoration = 'none';
  a.textContent = name + ' (' + sz + ')';
  w.appendChild(a);
  return w;
}





export function renderAttachmentPreview(att) {
  let el = document.getElementById('attachment-preview');
  if (!el) {
    el = document.createElement('div');
    el.id = 'attachment-preview';
    el.className = 'attachment-preview';
    const inputArea = document.querySelector('.chat-input-area');
    if (inputArea && inputArea.parentNode) {
      inputArea.parentNode.insertBefore(el, inputArea);
    } else {
      document.body.appendChild(el);
    }
  }
  if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
  if (!att) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  const list = Array.isArray(att) ? att : [att];
  if (list.length === 0) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  el.classList.add('active');
  el.style.display = 'block';
  el.innerHTML = '';
  el.innerHTML = '';
  list.forEach(function (a, idx) {
    const item = document.createElement('div');
    item.className = 'attachment-item';
    if (a.type === 'image' && a.file) {
      const img = document.createElement('img');
      img.className = 'attachment-thumb';
      try { img.src = URL.createObjectURL(a.file); } catch (_e) { img.src = ''; }
      img.alt = a.name || 'image';
      item.appendChild(img);
    } else {
      const icon = document.createElement('div');
      icon.className = 'attachment-file-icon';
      icon.textContent = '📎';
      item.appendChild(icon);
      const name = document.createElement('div');
      name.className = 'attachment-file-name';
      name.textContent = a.name || 'file';
      item.appendChild(name);
    }
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'attachment-remove';
    btn.textContent = '✕';
    btn.onclick = function () {
      if (window.chatState && Array.isArray(window.chatState.pendingAttachments)) {
        window.chatState.pendingAttachments.splice(idx, 1);
        renderAttachmentPreview(window.chatState.pendingAttachments);
      }
    };
    item.appendChild(btn);
    el.appendChild(item);
  });
}



export function renderImageBubble(content, role = 'user', senderName = null) {
  const raw = content.substring('[IMAGE]:'.length);
  const url = raw.split('|')[0].split(' ')[0].trim();
  const wrapper = document.createElement('div');
  wrapper.style.display = 'flex';
  wrapper.style.flexDirection = 'row';
  wrapper.style.alignItems = 'flex-start';
  wrapper.style.margin = '8px 12px';
  wrapper.style.justifyContent = (role === 'user') ? 'flex-end' : 'flex-start';
  const imgBox = document.createElement('div');
  imgBox.style.maxWidth = '180px';
  imgBox.style.borderRadius = '8px';
  imgBox.style.overflow = 'hidden';
  imgBox.style.cursor = 'pointer';
  const img = document.createElement('img');
  img.src = url;
  img.style.display = 'block';
  img.style.width = '100%';
  img.style.maxHeight = '240px';
  img.onclick = () => showImagePreview(url);
  imgBox.appendChild(img);
  const avatar = document.createElement('div');
  avatar.style.width = '36px';
  avatar.style.height = '36px';
  avatar.style.borderRadius = '50%';
  avatar.style.background = role === 'user' ? '#007aff' : '#e0e0e0';
  avatar.style.color = role === 'user' ? '#fff' : '#333';
  avatar.style.display = 'flex';
  avatar.style.alignItems = 'center';
  avatar.style.justifyContent = 'center';
  avatar.style.flexShrink = '0';
  avatar.style.fontSize = '16px';
  avatar.style.marginLeft = role === 'user' ? '8px' : '0';
  avatar.style.marginRight = role === 'user' ? '0' : '8px';
  avatar.textContent = (senderName || (role === 'user' ? '我' : 'AI')).charAt(0).toUpperCase();
  if (role === 'user') {
    wrapper.appendChild(imgBox);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(imgBox);
  }
  return wrapper;
}


export function renderRedPacketBubble(content) {

function renderTransferBubble(text) {
    const parts = String(text).replace('[TRANSFER]:', '').split('|');
    const amount = parts[0] || '0';
    const note = parts[1] || '';
    const el = document.createElement('div');
    el.className = 'transfer-bubble';
    el.style.cssText = 'background:#f59e0b;color:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;';
    el.innerHTML = '<div style="font-size:12px;">💰 转账</div><div style="font-size:18px;font-weight:bold;">' + amount + ' 积分</div>' + (note ? '<div style="font-size:12px;">' + note + '</div>' : '');
    return el;
}

  let data = {};
  try { data = JSON.parse(content.substring(12)); } catch (e) {}
  const div = document.createElement('div');
  div.className = 'red-packet-bubble';
  div.dataset.redPacketTx = data.tx_id || '';
  const t1 = document.createElement('div');
  t1.style.fontSize = '13px';
  t1.style.opacity = '0.9';
  t1.textContent = '🧧 红包';
  div.appendChild(t1);
  const t2 = document.createElement('div');
  t2.style.fontSize = '20px';
  t2.style.fontWeight = '700';
  t2.style.marginTop = '4px';
  t2.textContent = '¥' + (data.amount || 0);
  div.appendChild(t2);
  if (data.message) {
    const t3 = document.createElement('div');
    t3.style.fontSize = '12px';
    t3.style.opacity = '0.85';
    t3.style.marginTop = '4px';
    t3.textContent = data.message;
    div.appendChild(t3);
  }
  return div;
}

export function renderGroupRedPacketBubble(content) {
  let data = {};
  try { data = JSON.parse(content.substring(13)); } catch (e) {}
  const isPool = data.source_type === 'group_pool';
  const div = document.createElement('div');
  div.className = 'group-red-packet-bubble';
  const bg = isPool
    ? 'linear-gradient(135deg,#8b5cf6,#6366f1)'
    : 'linear-gradient(135deg,#f59e0b,#ef4444)';
  div.style.cssText = 'background:' + bg + ';color:#fff;padding:12px 16px;border-radius:12px;cursor:pointer;min-width:220px;';
  div.dataset.packetId = data.packet_id || '';
  const t1 = document.createElement('div');
  t1.style.fontSize = '13px';
  t1.style.opacity = '0.9';
  t1.textContent = isPool ? '🎁 群福利红包' : '🧧 群红包';
  div.appendChild(t1);
  const t2 = document.createElement('div');
  t2.style.fontSize = '20px';
  t2.style.fontWeight = '700';
  t2.style.marginTop = '4px';
  t2.textContent = (data.total_amount || 0) + ' 积分';
  div.appendChild(t2);
  const t3 = document.createElement('div');
  t3.style.fontSize = '12px';
  t3.style.opacity = '0.85';
  t3.style.marginTop = '4px';
  t3.textContent = '共 ' + (data.total_count || 0) + ' 份' + (isPool ? ' · 群池出资' : '');
  div.appendChild(t3);
  if (data.message) {
    const t4 = document.createElement('div');
    t4.style.fontSize = '12px';
    t4.style.opacity = '0.85';
    t4.style.marginTop = '4px';
    t4.textContent = data.message;
    div.appendChild(t4);
  }
  div.onclick = function() {
    if (typeof window.openGroupRedPacket === 'function') window.openGroupRedPacket(data.packet_id);
  };
  return div;
}




export function renderTaskCardBubble(content) {
  let data = {};
  try { data = JSON.parse(content.substring(12)); } catch (e) {}
  const div = document.createElement('div');
  div.className = 'task-card-bubble';
  div.style.cssText = 'background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:12px 16px;border-radius:12px;cursor:pointer;min-width:220px;';
  const t1 = document.createElement('div');
  t1.style.fontSize = '12px';
  t1.style.opacity = '0.9';
  t1.textContent = '\ud83d\udccc \u7fa4\u4efb\u52a1';
  div.appendChild(t1);
  const t2 = document.createElement('div');
  t2.style.fontSize = '15px';
  t2.style.fontWeight = '700';
  t2.style.marginTop = '6px';
  t2.textContent = data.title || '\u672a\u547d\u540d\u4efb\u52a1';
  div.appendChild(t2);
  const t3 = document.createElement('div');
  t3.style.fontSize = '12px';
  t3.style.opacity = '0.9';
  t3.style.marginTop = '4px';
  t3.textContent = '\u8d28\u62bc ' + (data.reward || 0) + ' \u79ef\u5206 \u00b7 ' + (data.status === 'open' ? '\u8fdb\u884c\u4e2d' : '\u5df2\u7ed3\u675f');
  div.appendChild(t3);
  div.dataset.taskId = data.task_id || '';
  div.onclick = function() {
    if (typeof window.openTaskDetail === 'function') window.openTaskDetail(data.task_id);
  };
  return div;
}


export function renderRedPacketDoneBubble(content) {
  let data = {};
  try { data = JSON.parse(content.substring(19)); } catch (e) {}
  const div = document.createElement('div');
  div.style.cssText = 'background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff;padding:12px 16px;border-radius:12px;min-width:220px;';
  const t1 = document.createElement('div');
  t1.style.fontSize = '13px';
  t1.style.opacity = '0.9';
  t1.textContent = '群红包已发放';
  div.appendChild(t1);
  const t2 = document.createElement('div');
  t2.style.fontSize = '20px';
  t2.style.fontWeight = '700';
  t2.style.marginTop = '6px';
  t2.textContent = '共 ' + (data.total || 0) + ' 积分';
  div.appendChild(t2);
  const t3 = document.createElement('div');
  t3.style.fontSize = '12px';
  t3.style.opacity = '0.9';
  t3.style.marginTop = '4px';
  t3.textContent = '已均分给 ' + (data.recipients || 0) + ' 位成员，人均 ' + (data.per_person || 0);
  div.appendChild(t3);
  return div;
}


export function updateMessageStatus(messageId, status) {
  const wrapper = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!wrapper) return;
  const existingStatus = wrapper.querySelector('.message-status');
  if (existingStatus) {
    if (status === 'sent') {
      existingStatus.remove();
    } else if (status === 'failed') {
      existingStatus.style.fontSize = '12px';
      existingStatus.style.color = '#ff3b30';
      existingStatus.style.alignSelf = 'center';
      existingStatus.style.marginRight = '8px';
      existingStatus.textContent = '发送失败';
      const retryBtn = document.createElement('button');
      retryBtn.textContent = '重试';
      retryBtn.style.fontSize = '12px';
      retryBtn.style.marginLeft = '4px';
      retryBtn.addEventListener('click', () => {
        const content = wrapper.dataset.content;
        const input = document.getElementById('chat-input');
        input.value = content;
        if (typeof window.updateSendButtonVisibility === 'function') {
          window.updateSendButtonVisibility();
        }
        if (typeof window.sendMessage === 'function') {
          window.sendMessage();
        }
        wrapper.remove();
      });
      existingStatus.appendChild(retryBtn);
    }
  } else if (status === 'failed') {
    const statusEl = document.createElement('span');
    statusEl.style.fontSize = '12px';
    statusEl.style.color = '#ff3b30';
    statusEl.style.alignSelf = 'center';
    statusEl.style.marginRight = '8px';
    statusEl.textContent = '发送失败';
    wrapper.appendChild(statusEl);
  }
}