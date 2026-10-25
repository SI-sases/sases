// static/modules/contributions.js
import { api } from './api.js';
import { t } from './i18n.js';

export async function openContributions() {
  let contribHtml = '';
  try {
    const data = await api.getCreditHistory(50);
    const history = data.history || [];
    if (history.length === 0) {
      contribHtml = `<div class="subpage-placeholder">${t('empty_contributions')}</div>`;
    } else {
      contribHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        contribHtml += `
          <div class="me-menu-item">
            <span class="menu-label">${item.action || '贡献'}</span>
            <span class="menu-value">${item.points > 0 ? '+' : ''}${item.points} ${t('credits')}</span>
          </div>
          <div style="padding:0 12px 8px;font-size:12px;color:#999;">${date} · ${item.detail || ''}</div>
        `;
      });
      contribHtml += '</div>';
    }
  } catch (e) {
    contribHtml = `<div class="subpage-placeholder">${t('load_failed')}</div>`;
  }
  window.openSubpage(t('my_contributions'), contribHtml);
}