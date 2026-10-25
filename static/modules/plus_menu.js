// static/modules/plus_menu.js
import { t } from './i18n.js';

export function showPlusMenu() {
  const view = document.querySelector('.nav-btn.active')?.dataset.view;
  let menuItems = [];

  if (view === 'messages') {
    menuItems = [
      { icon: '👥', label: t('start_group_chat'), action: () => window.openGroupChatList ? window.openGroupChatList() : window.openSubpage(t('start_group_chat'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`) },
      { icon: '🧑‍🤝‍🧑', label: t('add_agent'), action: () => window.openNewAgentPage ? window.openNewAgentPage() : window.openSubpage(t('add_agent'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`) },
      { icon: '📷', label: t('scan'), action: () => window.openSubpage(t('scan'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`) }
    ];
  } else if (view === 'contacts') {
    menuItems = [
      { icon: '🧑‍🤝‍🧑', label: t('add_agent'), action: () => window.openNewAgentPage ? window.openNewAgentPage() : window.openSubpage(t('add_agent'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`) },
      { icon: '👥', label: t('create_group'), action: () => window.openSubpage(t('create_group'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`) }
    ];
  } else if (view === 'discover') {
    menuItems = [
      { icon: '📷', label: t('scan'), action: () => window.openSubpage(t('scan'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`) },
      { icon: '🔄', label: t('refresh'), action: () => location.reload() }
    ];
  }

  if (menuItems.length === 0) return;

  const menu = document.getElementById('plus-menu');
  const content = menu ? menu.querySelector('.plus-menu-content') : null;
  if (!menu || !content) return;

  let html = '';
  menuItems.forEach(item => {
    html += `
      <div class="plus-menu-item">
        <span class="plus-menu-icon">${item.icon}</span>
        <span class="plus-menu-label">${item.label}</span>
      </div>
    `;
  });
  content.innerHTML = html;
  menu.style.display = 'block';

  content.querySelectorAll('.plus-menu-item').forEach((el, index) => {
    el.addEventListener('click', () => {
      closePlusMenu();
      const item = menuItems[index];
      if (item && item.action) item.action();
    });
  });

  const overlay = document.getElementById('plus-menu-overlay');
  if (overlay) overlay.onclick = closePlusMenu;
}

function closePlusMenu() {
  const menu = document.getElementById('plus-menu');
  if (menu) menu.style.display = 'none';
}