// static/modules/message_actions.js
import { api } from './api.js';
import { t } from './i18n.js';

let pendingQuote = null;

export function createContextMenu() {
  const oldMenu = document.getElementById('message-context-menu');
  if (oldMenu) oldMenu.remove();

  const menu = document.createElement('div');
  menu.id = 'message-context-menu';
  menu.className = 'message-context-menu';
  menu.style.display = 'none';
  document.body.appendChild(menu);
}

export function showContextMenu(x, y, wrapper) {
  const menu = document.getElementById('message-context-menu');
  if (!menu) return;
  menu.innerHTML = `
    <div class="context-menu-item" data-action="quote">${t('quote')}</div>
    <div class="context-menu-item" data-action="reply">${t('help_reply')}</div>
  `;
  menu.style.display = 'block';
  menu.style.left = x + 'px';
  menu.style.top = y + 'px';

  menu.querySelector('[data-action="quote"]').addEventListener('click', () => {
    pendingQuote = wrapper.dataset.content;
    showQuoteBar(pendingQuote);
    closeContextMenu();
  });

  menu.querySelector('[data-action="reply"]').addEventListener('click', async () => {
    const content = wrapper.dataset.content;
    try {
      const data = await api.suggestReply(content);
      const reply = data.response || t('no_suggestion');
      const input = document.getElementById('chat-input');
      if (input) {
        input.value = reply;
        if (window.updateSendButtonVisibility) window.updateSendButtonVisibility();
        input.focus();
      }
    } catch (e) {
      alert(t('generate_reply_failed') + ': ' + e.message);
    }
    closeContextMenu();
  });
}

export function closeContextMenu() {
  const menu = document.getElementById('message-context-menu');
  if (menu) menu.style.display = 'none';
}

export function attachLongPress(wrapper) {
  let timer = null;
  wrapper.addEventListener('touchstart', (e) => {
    const touch = e.touches[0];
    timer = setTimeout(() => {
      showContextMenu(touch.clientX, touch.clientY, wrapper);
    }, 800);
  }, { passive: true });

  wrapper.addEventListener('touchend', () => {
    if (timer) clearTimeout(timer);
  });
  wrapper.addEventListener('touchmove', () => {
    if (timer) clearTimeout(timer);
  });
}

function showQuoteBar(text) {
  let bar = document.getElementById('quote-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'quote-bar';
    bar.className = 'quote-bar';
    bar.innerHTML = `
      <span class="quote-text"></span>
      <button class="quote-close">×</button>
    `;
    const inputArea = document.querySelector('.chat-input-area');
    inputArea.parentElement.insertBefore(bar, inputArea);
    bar.querySelector('.quote-close').addEventListener('click', () => {
      pendingQuote = null;
      hideQuoteBar();
    });
  }
  bar.querySelector('.quote-text').textContent = text;
  bar.style.display = 'flex';
}

function hideQuoteBar() {
  const bar = document.getElementById('quote-bar');
  if (bar) bar.style.display = 'none';
}

export function getPendingQuote() {
  return pendingQuote;
}

export function clearPendingQuote() {
  pendingQuote = null;
  hideQuoteBar();
}