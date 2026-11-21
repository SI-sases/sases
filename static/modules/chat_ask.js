// static/modules/chat_ask.js
// ask_user v1：模型提问卡片，回答作为新消息发送
(function () {
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function show(d) {
    var box = document.getElementById('chat-messages');
    if (!box || !d || !d.question) return;
    var st = window.chatState || {};
    if (d.conversation_id && st.conversationId && String(d.conversation_id) !== String(st.conversationId)) return;
    var card = document.createElement('div');
    card.className = 'ask-card';
    card.style.cssText = 'margin:10px 14px;background:#f5f8ff;border:1px solid #cfe0ff;border-radius:10px;' +
      'padding:10px 12px;font-family:system-ui;font-size:12px;color:#333';
    card.innerHTML =
      '<div style="font-weight:600;color:#1a5fb4;margin-bottom:4px">🤔 需要你补充</div>' +
      '<div style="margin-bottom:8px;white-space:pre-wrap">' + esc(d.question) + '</div>' +
      '<div style="display:flex;gap:6px">' +
      '<input class="ask-input" style="flex:1;border:1px solid #ddd;border-radius:6px;padding:6px 8px;font-size:12px" placeholder="输入回答">' +
      '<button class="ask-send" style="border:none;background:#007aff;color:#fff;border-radius:6px;padding:6px 12px;font-size:12px;cursor:pointer">发送</button>' +
      '</div>';
    box.appendChild(card);
    box.scrollTop = box.scrollHeight;
    var input = card.querySelector('.ask-input');
    var btn = card.querySelector('.ask-send');
    input.focus();
    function send() {
      var text = (input.value || '').trim();
      if (!text) return;
      var chatInput = document.getElementById('chat-input');
      var sendBtn = document.getElementById('send-btn');
      if (!chatInput || !sendBtn) return;
      chatInput.value = text;
      chatInput.dispatchEvent(new Event('input', { bubbles: true }));
      btn.disabled = true;
      btn.textContent = '已回答';
      card.style.opacity = '0.75';
      sendBtn.click();
    }
    btn.onclick = send;
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); send(); }
    });
  }

  window.addEventListener('sases_ask_user', function (e) { show(e.detail || {}); });
})();
