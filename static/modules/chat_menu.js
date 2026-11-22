// static/modules/chat_menu.js
function openTransferDialog() {
  const chatState = window.chatState || {};
  const conversationId = chatState.conversationId;
  if (!conversationId) { alert(t('cm_enter_chat_first')); return; }
  
  // 自动获取当前聊天的对象
  // 优先读刚存的缓存，其次读 chatState，最后读 agentId（智能体聊天时）
  const receiverId = chatState.targetUserId || localStorage.getItem('sases_current_target_uid') || chatState.agentId;
  if (!receiverId) {
    alert(t('cm_no_transfer_target'));
    return;
  }

  let html = `
    <div style="padding: 20px; background: #f4f4f4; min-height: 100vh;">
      <div style="background: white; border-radius: 8px; overflow: hidden;">
        <div style="padding: 16px; border-bottom: 1px solid #eee; display: flex; align-items: center;">
          <span style="width: 80px; color: #666;">${t('cm_amount')}</span>
          <input type="number" id="transfer-amount" placeholder="0.00" style="flex:1; border:none; outline:none; font-size:24px; font-weight:bold; text-align:right;">
        </div>
        <div style="padding: 16px; border-bottom: 1px solid #eee; display: flex; align-items: center;">
          <span style="width: 80px; color: #666;">${t('cm_credit_type')}</span>
          <select id="transfer-type" style="flex:1; border:none; outline:none; text-align:right; font-size:16px;">
            <option value="credits">${t('seed_credits')}</option>
            <option value="compute">${t('compute_power')}</option>
          </select>
        </div>
        <div style="padding: 16px; display: flex; align-items: center;">
          <span style="width: 80px; color: #666;">${t('cm_note')}</span>
          <input type="text" id="transfer-note" placeholder="${t('cm_transfer_note_ph')}" style="flex:1; border:none; outline:none; text-align:right; font-size:16px;">
        </div>
      </div>
      <button id="btn-do-transfer" style="margin-top: 20px; width: 100%; padding: 14px; background: #f59e0b; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold;">${t('cm_transfer')}</button>
    </div>
  `;
  
  if (window.openSubpage) {
    window.openSubpage(t('cm_transfer'), html, { returnAction: () => { window.closeSubpage(); } });
    setTimeout(async () => {
      try {
        const token = localStorage.getItem('sases_token');
        const res = await fetch('/credits/balance', { headers: { Authorization: 'Bearer ' + token } });
        const data = await res.json();
        const hint = document.getElementById('transfer-balance-hint');
        if (hint && data.balance !== undefined) hint.textContent = t('cm_seed_balance') + data.balance;
      } catch(e) {}
    }, 50);

    setTimeout(() => {
      document.getElementById('btn-do-transfer').onclick = async () => {
        const amount = parseFloat(document.getElementById('transfer-amount').value);
        const type = document.getElementById('transfer-type').value;
        const note = document.getElementById('transfer-note').value;
        if (!amount || amount <= 0) { alert(t('cm_invalid_amount')); return; }
        
        // 二次确认（微信式）
        if (!confirm(t('cm_confirm_transfer').replace('{amount}', amount).replace('{type}', type === 'compute' ? t('compute_power') : t('seed_credits')))) return;

        try {
          // 直接调 api 发起请求
          const res = await window.sendTransfer(String(receiverId), amount, note, conversationId, type);
          if (res.status === 'completed' || res.tx_id) {
            alert(t('cm_transfer_ok'));
            window.closeSubpage();
            // 强制刷新聊天记录以显示气泡
            if (window.loadMessages && conversationId) {
              window.loadMessages(conversationId);
            }
            if (window.loadMessages) window.loadMessages(conversationId);
          } else {
            alert(t('cm_transfer_failed') + (res.error || res.err || t('cm_unknown_error')));
          }
        } catch (e) {
          alert(t('cm_transfer_failed') + (e.message || t('cm_network_error')));
        }
      };
    }, 100);
  }
}



function openRedPacketDialog() {
  const chatState = window.chatState || {};
  const conversationId = chatState.conversationId || null;

  const html = `
    <div class="red-packet-send-page">
      <div class="red-packet-header">
        <div class="red-packet-title">${t('cm_red_packet')}</div>
      </div>
      <div class="red-packet-body">
        <div class="red-packet-row">
          <label>${t('cm_amount')}</label>
          <input type="number" id="rp-amount" placeholder="0.00" min="0.01" step="0.01">
        </div>
        <div class="red-packet-row">
          <label>${t('cm_receiver')}</label>
          <input type="text" id="rp-receiver" placeholder="${t('cm_receiver_ph')}">
        </div>
        <div class="red-packet-row">
          <label>${t('cm_note')}</label>
          <input type="text" id="rp-message" placeholder="${t('cm_rp_default_msg')}" maxlength="30">
        </div>
      </div>
      <button id="rp-submit" class="red-packet-submit-btn">${t('cm_rp_submit')}</button>
    </div>
  `;
  window.openSubpage(t('cm_red_packet'), html, { showMore: false });

  setTimeout(() => {
    const submitBtn = document.getElementById('rp-submit');
    if (!submitBtn) return;
    submitBtn.addEventListener('click', async () => {
      const amount = parseFloat(document.getElementById('rp-amount').value);
      const receiver = document.getElementById('rp-receiver').value.trim();
      const message = document.getElementById('rp-message').value || t('cm_rp_default_msg');

      if (!amount || amount <= 0) { alert(t('cm_invalid_amount')); return; }
      if (!receiver) { alert(t('cm_receiver_required')); return; }

      submitBtn.disabled = true;
      submitBtn.textContent = t('cm_sending');
      try {
        await api.sendRedPacket(receiver, amount, message, conversationId);
        alert(t('cm_rp_sent'));
        window.closeSubpage && window.closeSubpage();
      } catch (e) {
        alert(t('cm_send_failed') + (e.message || t('cm_unknown_error')));
        submitBtn.disabled = false;
        submitBtn.textContent = t('cm_rp_submit');
      }
    });
  }, 100);
}
import { api } from './api.js';
import { openIdentitySwitch } from './chat_identity.js';
import { t } from './i18n.js';

// ========== 长按菜单 ==========
export function createContextMenu() {
  const oldMenu = document.getElementById('message-context-menu');
  if (oldMenu) oldMenu.remove();

  const menu = document.createElement('div');
  menu.id = 'message-context-menu';
  menu.style.position = 'fixed';
  menu.style.zIndex = '9999';
  menu.style.background = '#fff';
  menu.style.borderRadius = '8px';
  menu.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
  menu.style.display = 'none';
  document.body.appendChild(menu);
}

export function showContextMenu(x, y, wrapper, chatState) {
  const menu = document.getElementById('message-context-menu');
  if (!menu) return;
  const _isUserMsg = wrapper.dataset.role === 'user';
  menu.innerHTML = `
    <div class="context-menu-item" data-action="quote" style="padding:10px 16px; cursor:pointer;">${t('cm_quote')}</div>
    <div class="context-menu-item" data-action="reply" style="padding:10px 16px; cursor:pointer;">${t('cm_reply_for_me')}</div>
    <div class="context-menu-item" data-action="execute" style="padding:10px 16px; cursor:pointer;">${t('cm_execute_for_me')}</div>
    <div class="context-menu-item" data-action="copy" style="padding:10px 16px; cursor:pointer;">${t('cm_copy')}</div>
    <div class="context-menu-item" data-action="retry" style="padding:10px 16px; cursor:pointer;">${t('cm_retry')}</div>
    ${_isUserMsg ? '<div class="context-menu-item" data-action="edit" style="padding:10px 16px; cursor:pointer;">' + t('cm_edit') + '</div>' : ''}
    <div class="context-menu-item" data-action="delete" style="padding:10px 16px; cursor:pointer; color:#ff3b30;">${t('cm_delete')}</div>
  `;
  menu.style.display = 'block';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  menu.querySelector('[data-action="quote"]').addEventListener('click', () => {
    chatState.pendingQuote = wrapper.dataset.content;
    showQuoteBar(chatState.pendingQuote, chatState);
    closeContextMenu();
  });

  // FIX_MENU_V2: 帮我执行 → 填入草稿前缀（用户发送后出黄卡）
  menu.querySelector('[data-action="execute"]').addEventListener('click', async () => {
    // FIX_EXECUTE_V2: 收集上下文 → AI 生成 #4 指令 → 填入输入框
    const input = document.getElementById('chat-input');
    if (!input) { closeContextMenu(); return; }
    closeContextMenu();

    // 收集最近 5 条消息
    const _container = document.getElementById('chat-messages');
    const _recent = [];
    if (_container) {
      const _rows = Array.from(_container.querySelectorAll('.message-row')).slice(-5);
      for (const r of _rows) {
        const _isUser = r.classList.contains('user');
        const _bubble = r.querySelector('.message');
        const _txt = _bubble ? (_bubble.textContent || '').trim() : '';
        if (_txt) _recent.push({ role: _isUser ? 'user' : 'assistant', content: _txt });
      }
    }
    if (!_recent.length) {
      const _fallback = wrapper.dataset.content || '';
      if (_fallback) _recent.push({ role: 'user', content: _fallback });
    }

    const _oldPlaceholder = input.placeholder;
    input.placeholder = t('chatMenu.aiGenerating');
    input.disabled = true;

    try {
      const _data = await api.suggestExecute(_recent);
      const _ins = (_data && (_data.instruction || _data.task)) || '';
      if (!_ins) throw new Error(t('chatMenu.emptyInstruction'));
      input.value = _ins;
      if (typeof window.updateSendButtonVisibility === 'function') window.updateSendButtonVisibility();
    } catch (e) {
      console.error('[execute] generate failed:', e);
      const _fb = wrapper.dataset.content || '';
      input.value = t('cm_reply_prefix') + _fb.slice(0, 300);
      if (typeof window.updateSendButtonVisibility === 'function') window.updateSendButtonVisibility();
    } finally {
      input.placeholder = _oldPlaceholder || t('cm_input_ph');
      input.disabled = false;
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  });

  menu.querySelector('[data-action="copy"]').addEventListener('click', async () => {
    const text = wrapper.dataset.content || '';
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
      }
    } catch (e) {
      console.warn('[menu] copy failed', e);
    }
    closeContextMenu();
  });

  menu.querySelector('[data-action="retry"]').addEventListener('click', () => {
    const text = wrapper.dataset.content || '';
    const input = document.getElementById('chat-input');
    closeContextMenu();
    if (!input || !text) return;
    input.value = text;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
    const btn = document.getElementById('send-btn');
    if (btn) btn.click();
  });

  const _editBtn = menu.querySelector('[data-action="edit"]');
  if (_editBtn) {
    _editBtn.addEventListener('click', () => {
      const text = wrapper.dataset.content || '';
      const input = document.getElementById('chat-input');
      closeContextMenu();
      if (!input) return;
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
      input.setSelectionRange(text.length, text.length);
    });
  }

  // FIX_MENU_V2: 删除单条消息
  menu.querySelector('[data-action="delete"]').addEventListener('click', async () => {
    const messageId = wrapper.dataset.messageId;
    if (!messageId) { alert(t('cm_no_message')); return; }
    if (!confirm(t('cm_delete_confirm'))) { closeContextMenu(); return; }
    try {
      const token = localStorage.getItem('sases_token') || '';
      const resp = await fetch('/messages/message/' + messageId, {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (resp.ok) {
        wrapper.remove();
      } else if (resp.status === 404) {
        alert(t('cm_delete_unavailable'));
      } else {
        alert(t('cm_delete_failed') + ' HTTP ' + resp.status);
      }
    } catch (e) {
      alert(t('cm_delete_failed') + ' ' + (e.message || e));
    }
    closeContextMenu();
  });

  menu.querySelector('[data-action="reply"]').addEventListener('click', async () => {
    const content = wrapper.dataset.content;
    // 群聊：弹智能体选择
    if (chatState && chatState.isGroup && chatState.groupId) {
      closeContextMenu();
      if (typeof window.openGroupAgentPickerForReply === 'function') {
        window.openGroupAgentPickerForReply(content, chatState.groupId);
      }
      return;
    }
    // 单聊：原逻辑
    try {
      const data = await api.suggestReply(content);
      const reply = data.response || t('cm_no_suggestion');
      const input = document.getElementById('chat-input');
      if (input) {
        input.value = reply;
        if (typeof window.updateSendButtonVisibility === 'function') {
          window.updateSendButtonVisibility();
        }
        input.focus();
      }
    } catch (e) {
      alert(t('cm_generate_failed') + e.message);
    }
    closeContextMenu();
  });
}

export function closeContextMenu() {
  const menu = document.getElementById('message-context-menu');
  if (menu) menu.style.display = 'none';
}

export function attachLongPress(wrapper, chatState) {
  let timer = null;
  wrapper.addEventListener('touchstart', (e) => {
    const touch = e.touches[0];
    timer = setTimeout(() => {
      showContextMenu(touch.clientX, touch.clientY, wrapper, chatState);
    }, 800);
  }, { passive: true });

  wrapper.addEventListener('touchend', () => {
    if (timer) clearTimeout(timer);
  });
  wrapper.addEventListener('touchmove', () => {
    if (timer) clearTimeout(timer);
  });

  // PC 端：右键弹出菜单
  wrapper.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    showContextMenu(e.clientX, e.clientY, wrapper, chatState);
  });
}

// 将 attachLongPress 挂到 window，方便 chat_ui.js 调用
window.attachLongPress = attachLongPress;

// ========== 引用条 ==========
export function showQuoteBar(text, chatState) {
  let bar = document.getElementById('quote-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'quote-bar';
    bar.style.display = 'flex';
    bar.style.alignItems = 'center';
    bar.style.justifyContent = 'space-between';
    bar.style.padding = '8px 12px';
    bar.style.background = '#f7f7f7';
    bar.style.borderRadius = '8px';
    bar.style.margin = '0 12px 8px';
    bar.innerHTML = `
      <span class="quote-text" style="flex:1; color:#666; font-size:14px;"></span>
      <button class="quote-close" style="background:none; border:none; font-size:18px; cursor:pointer;">×</button>
    `;
    const inputArea = document.querySelector('.chat-input-area');
    inputArea.parentElement.insertBefore(bar, inputArea);
    bar.querySelector('.quote-close').addEventListener('click', () => {
      chatState.pendingQuote = null;
      hideQuoteBar();
    });
  }
  bar.querySelector('.quote-text').textContent = text;
  bar.style.display = 'flex';
}

export function hideQuoteBar() {
  const bar = document.getElementById('quote-bar');
  if (bar) bar.style.display = 'none';
}

// ========== 聊天信息页 ==========
export function openChatInfo(chatState) {
  const chatName = document.getElementById('chat-window-title').textContent;
  const contentHtml = `
    <div class="chat-info-header">
      <div class="chat-info-avatar">${chatName.charAt(0)}</div>
      <div class="chat-info-name">${chatName}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="switch-identity-entry">
        <span class="menu-label">${t('cm_switch_identity')}</span>
        <span class="menu-value" id="current-identity-text">${chatState.senderAgentId ? t('cm_identity_agent') : t('cm_identity_self')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="set-remark-entry">
        <span class="menu-label">${t('cm_set_remark')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="complain-entry">
        <span class="menu-label">${t('cm_complain')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="delete-chat-entry">
        <span class="menu-label" style="color:#ff3b30;">${t('cm_delete_chat')}</span>
      </div>
    </div>
  `;
  window.openSubpage(t('cm_chat_info'), contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('switch-identity-entry').addEventListener('click', () => openIdentitySwitch(chatState, api));
    document.getElementById('set-remark-entry').addEventListener('click', () => {
      const remark = prompt(t('cm_remark_prompt'), chatName);
      if (remark) alert(t('cm_remark_set'));
    });
    document.getElementById('complain-entry').addEventListener('click', () => alert(t('cm_complain_todo')));
    document.getElementById('delete-chat-entry').addEventListener('click', () => {
      if (confirm(t('cm_confirm_delete_chat'))) alert(t('cm_chat_deleted'));
    });
  }, 100);
}

// ========== 加号面板 ==========
export function toggleChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  if (panel.style.display === 'block') {
    closeChatPlusPanel();
  } else {
    openChatPlusPanel();
  }
}

export function openChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  const content = document.getElementById('chat-plus-content');
  if (content) {
    const items = [
      { icon: '📷', label: t('cm_album'), action: () => { const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/*'; inp.multiple = true; inp.onchange = () => { if (!inp.files || !inp.files.length) return; window.chatState = window.chatState || {}; window.chatState.pendingAttachments = window.chatState.pendingAttachments || []; Array.from(inp.files).forEach(f => { window.chatState.pendingAttachments.push({ type: 'image', file: f, name: f.name, size: f.size }); }); import('./chat_ui.js').then(m => m.renderAttachmentPreview(window.chatState.pendingAttachments)); }; inp.click(); } },
      { icon: '💰', label: t('cm_transfer'), action: () => openTransferDialog() },
      ...(window.currentGroupId ? [] : [{ icon: '🧧', label: t('cm_red_packet'), action: () => openRedPacketDialog() },]),
{ icon: '📁', label: t('cm_file'), action: () => { const inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true; inp.onchange = () => { if (!inp.files || !inp.files.length) return; window.chatState = window.chatState || {}; window.chatState.pendingAttachments = window.chatState.pendingAttachments || []; Array.from(inp.files).forEach(f => { window.chatState.pendingAttachments.push({ type: 'file', file: f, name: f.name, size: f.size }); }); import('./chat_ui.js').then(m => m.renderAttachmentPreview(window.chatState.pendingAttachments)); }; inp.click(); } },
      { icon: '📍', label: t('cm_location'), action: () => alert(t('cm_location_todo')) }
    ];
if (window.currentGroupId) {

    items.push({
      icon: '🧧',
      label: t('cm_group_red_packet'),
      badge_id: 'rp-badge',
      action: () => {
        if (typeof window.openGroupRedPacketDialog === 'function') window.openGroupRedPacketDialog(window.currentGroupId);
      }
    });
    items.push({
      icon: '📌',
      label: t('cm_publish_task'),
      action: () => {
        if (typeof window.openPublishTaskDialog === 'function') window.openPublishTaskDialog(window.currentGroupId);
      }
    });
  }
  
    let html = '<div class="chat-plus-grid">';
    items.forEach(item => {
      html += `
        <div class="chat-plus-item"${item.badge_id ? ' data-badge-id="' + item.badge_id + '"' : ''}>
          <div class="chat-plus-icon">${item.icon}${item.badge_id ? '<span class="chat-plus-badge" data-badge="' + item.badge_id + '" style="display:none;"></span>' : ''}</div>
          <div class="chat-plus-label">${item.label}</div>
        </div>
      `;
    });
    html += '</div>';
    content.innerHTML = html;
    content.querySelectorAll('.chat-plus-item').forEach((el, index) => {
      el.addEventListener('click', () => {
        closeChatPlusPanel();
        items[index].action();
      });
    });
  }
  panel.style.display = 'block';
  if (window.currentGroupId) {
    import('./api.js').then(m => {
      m.api.getActiveGroupRedPackets(window.currentGroupId).then(d => {
        const n = (d && d.packets || []).length;
        const badge = document.querySelector('[data-badge="rp-badge"]');
        if (badge && n > 0) {
          badge.textContent = n;
          badge.style.display = 'inline-block';
        }
      }).catch(() => {});
    });
  }
}

export function closeChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (panel) panel.style.display = 'none';
}

// 点击外部关闭长按菜单
document.addEventListener('click', (e) => {
  const menu = document.getElementById('message-context-menu');
  if (menu && !menu.contains(e.target)) {
    closeContextMenu();
  }
});

// chat-plus-panel-outside-close: v6
const _cpOverlay = document.getElementById('chat-plus-overlay');
if (_cpOverlay) {
  _cpOverlay.addEventListener('click', function() {
    const panel = document.getElementById('chat-plus-panel');
    if (panel) panel.style.display = 'none';
  });
}
document.body.addEventListener('click', function(e) {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  const cs = window.getComputedStyle(panel);
  if (cs.display === 'none' || cs.visibility === 'hidden') return;
  if (panel.contains(e.target)) return;
  const plusBtn = document.getElementById('input-plus-btn');
  if (plusBtn && (plusBtn === e.target || plusBtn.contains(e.target))) return;
  panel.style.display = 'none';
});
