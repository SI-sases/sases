// static/modules/search.js
import { api } from './api.js';
import { t } from './i18n.js';

export async function openGlobalSearch() {
  const contentHtml = `
    <div class="subpage-search-bar">
      <input type="text" class="search-input" id="global-search-input" placeholder="${t('search_placeholder_global')}">
      <button class="search-btn" id="global-search-btn">${t('search')}</button>
    </div>
    <div id="global-search-results"></div>
  `;
  window.openSubpage(t('search'), contentHtml);

  setTimeout(() => {
    const searchBtn = document.getElementById('global-search-btn');
    const searchInput = document.getElementById('global-search-input');
    if (!searchBtn || !searchInput) return;

    searchBtn.addEventListener('click', () => {
      const q = searchInput.value.trim();
      if (q) performGlobalSearch(q);
    });
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim();
        if (q) performGlobalSearch(q);
      }
    });
  }, 100);
}

async function performGlobalSearch(q) {
  const resultsContainer = document.getElementById('global-search-results');
  if (!resultsContainer) return;
  resultsContainer.innerHTML = '<div class="subpage-placeholder">搜索中...</div>';
  try {
    const data = await api.globalSearch(q);
    renderSearchResults(data);
  } catch (e) {
    resultsContainer.innerHTML = `<div class="subpage-placeholder">${t('search_failed')}: ${e.message}</div>`;
  }
}

function renderSearchResults(data) {
  const container = document.getElementById('global-search-results');
  if (!container) return;
  let html = '';

  if (data.users && data.users.length > 0) {
    html += `<div class="section-title">${t('users')}</div><div class="me-menu">`;
    data.users.forEach(user => {
      html += `
        <div class="me-menu-item">
          <span class="menu-icon">👤</span>
          <div class="menu-text">
            <div class="menu-title">${user.username}</div>
            <div class="menu-desc">${user.sases_id || ''}</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  if (data.agents && data.agents.length > 0) {
    html += `<div class="section-title">${t('ai_agents')}</div><div class="me-menu">`;
    data.agents.forEach(agent => {
      html += `
        <div class="me-menu-item">
          <span class="menu-icon">🤖</span>
          <div class="menu-text">
            <div class="menu-title">${agent.name}</div>
            <div class="menu-desc">${agent.owner_name} · ${agent.provider || agent.model_name}</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  if (data.knowledge && data.knowledge.length > 0) {
    html += `<div class="section-title">${t('knowledge_base')}</div><div class="me-menu">`;
    data.knowledge.forEach(item => {
      html += `
        <div class="me-menu-item">
          <span class="menu-icon">📚</span>
          <div class="menu-text">
            <div class="menu-title">${item.task}</div>
            <div class="menu-desc">${item.solution.substring(0, 50)}...</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  if (!html) {
    html = `<div class="subpage-placeholder">${t('no_results')}</div>`;
  }
  container.innerHTML = html;
}