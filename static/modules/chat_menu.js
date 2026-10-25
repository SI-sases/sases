// static/modules/chat_menu.js
function openTransferDialog() {
  const receiver = prompt('收款人 SASES ID：');
  if (!receiver) return;
  const amountStr = prompt('转账金额：');
  if (!amountStr) return;
  const amount = parseFloat(amountStr);
  if (!amount || amount <= 0) { alert('金额无效'); return; }
  const note = prompt('留言（可选）：') || '';
  const cid = window.chatState && window.chatState.conversationId;
  if (!cid) { alert('请先进入会话'); return; }
  if (typeof window.sendTransfer === 'function') {
    window.sendTransfer(receiver, amount, note, cid);
  } else {
    alert('sendTransfer 未就绪');
  }
}



function openRedPacketDialog() {
  const chatState = window.chatState || {};
  const conversationId = chatState.conversationId || null;

  const html = `
    <div class="red-packet-send-page">
      <div class="red-packet-header">
        <div class="red-packet-title">发红包</div>
      </div>
      <div class="red-packet-body">
        <div class="red-packet-row">
          <label>金额</label>
          <input type="number" id="rp-amount" placeholder="0.00" min="0.01" step="0.01">
        </div>
        <div class="red-packet-row">
          <label>接收者</label>
          <input type="text" id="rp-receiver" placeholder="SASES ID 或用户ID">
        </div>
        <div class="red-packet-row">
          <label>留言</label>
          <input type="text" id="rp-message" placeholder="恭喜发财，大吉大利" maxlength="30">
        </div>
      </div>
      <button id="rp-submit" class="red-packet-submit-btn">塞钱进红包</button>
    </div>
  `;
  window.openSubpage('发红包', html, { showMore: false });

  setTimeout(() => {
    const submitBtn = document.getElementById('rp-submit');
    if (!submitBtn) return;
    submitBtn.addEventListener('click', async () => {
      const amount = parseFloat(document.getElementById('rp-amount').value);
      const receiver = document.getElementById('rp-receiver').value.trim();
      const message = document.getElementById('rp-message').value || '恭喜发财，大吉大利';

      if (!amount || amount <= 0) { alert('请输入有效金额'); return; }
      if (!receiver) { alert('请输入接收者的 SASES ID'); return; }

      submitBtn.disabled = true;
      submitBtn.textContent = '发送中...';
      try {
        await api.sendRedPacket(receiver, amount, message, conversationId);
        alert('红包已发出');
        window.closeSubpage && window.closeSubpage();
      } catch (e) {
        alert('发送失败：' + (e.message || '未知错误'));
        submitBtn.disabled = false;
        submitBtn.textContent = '塞钱进红包';
      }
    });
  }, 100);
}
import { api } from './api.js';
import { openIdentitySwitch } from './chat_identity.js';

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
  menu.innerHTML = `
    <div class="context-menu-item" data-action="quote" style="padding:10px 16px; cursor:pointer;">引用</div>
    <div class="context-menu-item" data-action="reply" style="padding:10px 16px; cursor:pointer;">帮我回复</div>
  `;
  menu.style.display = 'block';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  menu.querySelector('[data-action="quote"]').addEventListener('click', () => {
    chatState.pendingQuote = wrapper.dataset.content;
    showQuoteBar(chatState.pendingQuote, chatState);
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
      const reply = data.response || '（无建议）';
      const input = document.getElementById('chat-input');
      if (input) {
        input.value = reply;
        if (typeof window.updateSendButtonVisibility === 'function') {
          window.updateSendButtonVisibility();
        }
        input.focus();
      }
    } catch (e) {
      alert('生成回复失败：' + e.message);
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
        <span class="menu-label">切换身份</span>
        <span class="menu-value" id="current-identity-text">${chatState.senderAgentId ? '智能体身份' : '以本人身份'}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="set-remark-entry">
        <span class="menu-label">设置备注和标签</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="complain-entry">
        <span class="menu-label">投诉</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="delete-chat-entry">
        <span class="menu-label" style="color:#ff3b30;">删除聊天</span>
      </div>
    </div>
  `;
  window.openSubpage('聊天信息', contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('switch-identity-entry').addEventListener('click', () => openIdentitySwitch(chatState, api));
    document.getElementById('set-remark-entry').addEventListener('click', () => {
      const remark = prompt('请输入备注名：', chatName);
      if (remark) alert('备注已设置（模拟）');
    });
    document.getElementById('complain-entry').addEventListener('click', () => alert('投诉功能待实现'));
    document.getElementById('delete-chat-entry').addEventListener('click', () => {
      if (confirm('确定删除聊天记录吗？')) alert('已删除（模拟）');
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
      { icon: '📷', label: '相册', action: () => { const inp = document.createElement('input'); inp.type = 'file'; inp.accept = 'image/*'; inp.multiple = true; inp.onchange = () => { if (!inp.files || !inp.files.length) return; window.chatState = window.chatState || {}; window.chatState.pendingAttachments = window.chatState.pendingAttachments || []; Array.from(inp.files).forEach(f => { window.chatState.pendingAttachments.push({ type: 'image', file: f, name: f.name, size: f.size }); }); import('./chat_ui.js').then(m => m.renderAttachmentPreview(window.chatState.pendingAttachments)); }; inp.click(); } },
      { icon: '💰', label: '转账', action: () => openTransferDialog() },
      ...(window.currentGroupId ? [] : [{ icon: '🧧', label: '红包', action: () => openRedPacketDialog() },]),
{ icon: '📁', label: '文件', action: () => { const inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true; inp.onchange = () => { if (!inp.files || !inp.files.length) return; window.chatState = window.chatState || {}; window.chatState.pendingAttachments = window.chatState.pendingAttachments || []; Array.from(inp.files).forEach(f => { window.chatState.pendingAttachments.push({ type: 'file', file: f, name: f.name, size: f.size }); }); import('./chat_ui.js').then(m => m.renderAttachmentPreview(window.chatState.pendingAttachments)); }; inp.click(); } },
      { icon: '📍', label: '位置', action: () => alert('位置功能待实现') }
    ];
if (window.currentGroupId) {

    items.push({
      icon: '🧧',
      label: '群红包',
      badge_id: 'rp-badge',
      action: () => {
        if (typeof window.openGroupRedPacketDialog === 'function') window.openGroupRedPacketDialog(window.currentGroupId);
      }
    });
    items.push({
      icon: '📌',
      label: '发任务',
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
