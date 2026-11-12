// static/modules/sidebar.js
import { api } from './api.js';
import { t } from './i18n.js';
import { openMarketPage } from './market.js';

export function initSideDrawer() {
  const hamburgerBtn = document.getElementById('hamburger-btn');
  const drawer = document.getElementById('side-drawer');
  const overlay = document.getElementById('side-drawer-overlay');
  if (!hamburgerBtn || !drawer || !overlay) return;

  hamburgerBtn.addEventListener('click', () => {
    updateSidebarTexts();
    drawer.style.display = 'block';
    setTimeout(() => drawer.classList.add('open'), 10);
  });

  overlay.addEventListener('click', () => {
    drawer.classList.remove('open');
    setTimeout(() => drawer.style.display = 'none', 300);
  });

  const menuHarness = document.getElementById('menu-harness');
  const menuMarket = document.getElementById('menu-market');
  const menuMiniApps = document.getElementById('menu-mini-apps');
  const pollinationToggle = document.getElementById('pollination-toggle');

  if (menuHarness) {
    menuHarness.addEventListener('click', () => {
      closeSideDrawer();
      window.openSubpage(t('harness_tools'), `<div class="subpage-placeholder">${t('loading')}...</div>`);
      loadHarnessTools();
    });
  }
  if (menuMarket) {
    menuMarket.addEventListener('click', () => {
      closeSideDrawer();
      openMarketPage();
    });
  }
  if (menuMiniApps) {
    menuMiniApps.addEventListener('click', () => {
      closeSideDrawer();
      window.openSubpage(t('mini_apps'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`);
    });
  }
  // v0.18.2: 授粉已自动化，移除手动开关

  // 初始更新文本
  updateSidebarTexts();

  // 监听语言变化
  window.addEventListener('langchange', updateSidebarTexts);
}

function updateSidebarTexts() {
  // 更新标题
  const headerSpan = document.querySelector('.side-drawer-header span');
  if (headerSpan) headerSpan.textContent = t('side_menu');

  // 更新各菜单项的标签文本
  const setLabel = (selector, key) => {
    const item = document.querySelector(selector);
    if (item) {
      // 找到除了图标和箭头以外的 span
      const labels = item.querySelectorAll('span:not(.menu-icon):not(.menu-arrow)');
      if (labels.length > 0) {
        // 通常只有一个标签，取第一个
        labels[0].textContent = t(key);
      }
    }
  };

  setLabel('#menu-harness', 'harness_tools');
  setLabel('#menu-pollination-switch', 'pollination_switch');
  setLabel('#menu-market', 'market');
  setLabel('#menu-mini-apps', 'mini_apps');
}

function closeSideDrawer() {
  const drawer = document.getElementById('side-drawer');
  if (drawer) {
    drawer.classList.remove('open');
    setTimeout(() => drawer.style.display = 'none', 300);
  }
}

async function loadHarnessTools() {
  try {
    const data = await api.getHarnessModules();
    const modules = data.modules || [];
    let html = '';
    if (modules.length === 0) {
      html = `<div class="subpage-placeholder">${t('no_modules')}</div>`;
    } else {
      html = '<div class="me-menu">';
      modules.forEach(mod => {
        html += `
          <div class="me-menu-item">
            <span class="menu-icon">🔧</span>
            <div class="menu-text">
              <div class="menu-title">${mod.name}</div>
              <div class="menu-desc">${mod.description || mod.id}</div>
            </div>
          </div>
        `;
      });
      html += '</div>';
    }
    document.getElementById('subpage-content').innerHTML = html;
  } catch (e) {
    document.getElementById('subpage-content').innerHTML = `<div class="subpage-placeholder">${t('load_failed')}</div>`;
  }
}