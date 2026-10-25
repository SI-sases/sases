// static/modules/me_memory.js
import { api } from './api.js';
import { t } from './me_i18n.js';

// ==================== 记忆管理 ====================
export async function openMemoryManager() {
  const contentHtml = `
    <div class="subpage-search-bar" style="margin-bottom:10px;">
      <input type="text" id="memory-search-input" class="search-input" placeholder="${t('search')}">
      <button id="memory-search-btn" class="search-btn">${t('search')}</button>
    </div>
    <div id="memory-list-container" class="me-menu">
      <div class="subpage-placeholder">${t('loading')}</div>
    </div>
  `;
  window.openSubpage(t('memory_management'), contentHtml);

  loadMemories('task_result');

  setTimeout(() => {
    document.getElementById('memory-search-btn').onclick = () => {
      const q = document.getElementById('memory-search-input').value.trim();
      if (q) searchMemories(q);
    };
    document.getElementById('memory-search-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const q = document.getElementById('memory-search-input').value.trim();
        if (q) searchMemories(q);
      }
    });
  }, 100);
}

async function loadMemories(memoryType) {
  const container = document.getElementById('memory-list-container');
  if (!container) return;
  container.innerHTML = `<div class="subpage-placeholder">${t('loading')}</div>`;
  try {
    const data = await api.getMemoryByType(memoryType, 20);
    const memories = data.memories || [];
    renderMemories(memories, container);
  } catch (e) {
    container.innerHTML = `<div class="subpage-placeholder">${t('loading_failed') || '加载失败'}: ${e.message}</div>`;
  }
}

async function searchMemories(query) {
  const container = document.getElementById('memory-list-container');
  if (!container) return;
  container.innerHTML = `<div class="subpage-placeholder">${t('loading')}</div>`;
  try {
    const data = await api.recallMemory(query, 20);
    const memories = data.memories || [];
    renderMemories(memories, container);
  } catch (e) {
    container.innerHTML = `<div class="subpage-placeholder">${t('loading_failed') || '加载失败'}: ${e.message}</div>`;
  }
}

function renderMemories(memories, container) {
  if (!container) return;
  if (memories.length === 0) {
    container.innerHTML = `<div class="subpage-placeholder">${t('no_memory')}</div>`;
    return;
  }
  let html = '<div class="me-menu">';
  memories.forEach(mem => {
    const date = new Date(mem.created_at).toLocaleString('zh-CN');
    html += `
      <div class="me-menu-item memory-item" data-memory-id="${mem.id}">
        <div class="menu-text">
          <div class="menu-title">${mem.content.substring(0, 80)}</div>
          <div class="menu-desc">${t('type')}: ${mem.memory_type} · ${t('importance')}: ${mem.importance} · ${date}</div>
        </div>
        <button class="delete-memory-btn" data-memory-id="${mem.id}">${t('delete')}</button>
      </div>
    `;
  });
  html += '</div>';
  container.innerHTML = html;

  container.querySelectorAll('.delete-memory-btn').forEach(btn => {
    btn.onclick = async (e) => {
      e.stopPropagation();
      const memoryId = btn.dataset.memoryId;
      if (!confirm(t('delete_confirm') + '?')) return;
      try {
        await api.deleteMemory(memoryId);
        alert(t('delete_success'));
        loadMemories('task_result');
      } catch (err) {
        alert(t('delete_failed') + ': ' + err.message);
      }
    };
  });
}

// 挂载到全局，供设置页面调用
window.openMemoryManager = openMemoryManager;