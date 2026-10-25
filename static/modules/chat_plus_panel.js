// static/modules/chat_plus_panel.js
import { t } from './i18n.js';

export function toggleChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  if (panel.style.display === 'block') {
    closeChatPlusPanel();
  } else {
    openChatPlusPanel();
  }
}

function openChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (!panel) return;
  const content = document.getElementById('chat-plus-content');
  if (content) {
    const items = [
      { icon: '📷', label: t('album'), action: () => alert(t('album') + ' ' + t('coming_soon')) },
      { icon: '💰', label: t('transfer'), action: () => alert(t('transfer') + ' ' + t('coming_soon')) },
      { icon: '🧧', label: t('red_packet'), action: () => alert(t('red_packet') + ' ' + t('coming_soon')) },
      { icon: '📁', label: t('file'), action: () => alert(t('file') + ' ' + t('coming_soon')) },
      { icon: '📍', label: t('location'), action: () => alert(t('location') + ' ' + t('coming_soon')) }
    ];
    let html = '<div class="chat-plus-grid">';
    items.forEach(item => {
      html += `
        <div class="chat-plus-item">
          <div class="chat-plus-icon">${item.icon}</div>
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
}

export function closeChatPlusPanel() {
  const panel = document.getElementById('chat-plus-panel');
  if (panel) panel.style.display = 'none';
}