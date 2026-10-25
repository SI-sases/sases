// static/modules/knowledge.js
import { api } from './api.js';
import { t } from './i18n.js';

export async function openKnowledgeBase() {
  let knowledgeHtml = '';
  try {
    const data = await api.listKnowledge();
    const knowledge = data.knowledge || [];
    if (knowledge.length === 0) {
      knowledgeHtml = `<div class="subpage-placeholder">${t('empty_knowledge')}</div>`;
    } else {
      knowledgeHtml = '<div class="me-menu">';
      knowledge.forEach(item => {
        const verifiedIcon = item.verified ? '✅' : '❌';
        knowledgeHtml += `
          <div class="me-menu-item">
            <span class="menu-icon">${verifiedIcon}</span>
            <div class="menu-text">
              <div class="menu-title">${item.task}</div>
              <div class="menu-desc">${item.solution.substring(0, 50)}...</div>
            </div>
          </div>
        `;
      });
      knowledgeHtml += '</div>';
    }
  } catch (e) {
    knowledgeHtml = `<div class="subpage-placeholder">${t('load_failed')}</div>`;
  }
  window.openSubpage(t('knowledge_base'), knowledgeHtml);
}