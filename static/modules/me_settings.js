// static/modules/me_settings.js
import { api } from './api.js';
import { t } from './me_i18n.js';

// ==================== 设置 ====================
export function openSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="set-account"><span class="menu-label">${t('account_security')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-pollination"><span class="menu-label">${t('pollination_plan')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-memory"><span class="menu-label">${t('memory_management')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-notify"><span class="menu-label">${t('notification_settings')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-privacy"><span class="menu-label">${t('privacy')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-language"><span class="menu-label">${t('language_settings')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-about"><span class="menu-label">${t('about_sases')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="set-logout" style="justify-content:center;"><span class="menu-label" style="color:#ff3b30;">${t('logout')}</span></div>
    </div>
  `;
  window.openSubpage(t('settings'), contentHtml);

  setTimeout(() => {
    document.getElementById('set-account').onclick = openAccountSettings;
    document.getElementById('set-pollination').onclick = openPollinationPlan;
    document.getElementById('set-memory').onclick = () => {
      if (typeof window.openMemoryManager === 'function') window.openMemoryManager();
      else alert(t('memory_management') + ' - ' + t('coming_soon'));
    };
    document.getElementById('set-notify').onclick = openNotificationSettings;
    document.getElementById('set-privacy').onclick = openPrivacySettings;
    document.getElementById('set-language').onclick = openLanguageSettings;
    document.getElementById('set-about').onclick = openAboutPage;
    document.getElementById('set-logout').onclick = () => {
      localStorage.removeItem('sases_token');
      localStorage.removeItem('sases_username');
      localStorage.removeItem('sases_user_id');
      localStorage.removeItem('sases_sas_id');
      localStorage.removeItem('sases_credits_cache');
      window.location.reload();
    };
  }, 100);
}

function openAccountSettings() {
  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || t('not_set');
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('nickname')}</span><span class="menu-value">${username}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('sases_id')}</span><span class="menu-value">${sasesId}</span></div>
      <div class="me-menu-item" id="account-change-password"><span class="menu-label">${t('change_password')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="account-logout-devices"><span class="menu-label">${t('device_management')}</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage(t('account_security'), contentHtml);
  setTimeout(() => {
    document.getElementById('account-change-password').onclick = () => alert(t('change_password') + ' - ' + t('coming_soon'));
    document.getElementById('account-logout-devices').onclick = () => alert(t('device_management') + ' - ' + t('coming_soon'));
  }, 100);
}

function openNotificationSettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('receive_new_message')}</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">${t('agent_dynamic')}</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">${t('credit_change')}</span><label class="switch"><input type="checkbox" checked><span class="slider"></span></label></div>
      <div class="me-menu-item"><span class="menu-label">${t('bounty_task')}</span><label class="switch"><input type="checkbox"><span class="slider"></span></label></div>
    </div>
  `;
  window.openSubpage(t('notification_settings'), contentHtml);
}

function openPrivacySettings() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('who_can_see_agents')}</span><span class="menu-value">${t('friends_only')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('who_can_search_me')}</span><span class="menu-value">${t('everyone')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="privacy-export-data"><span class="menu-label">${t('export_data')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="privacy-delete-data"><span class="menu-label">${t('delete_cloud_data')}</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage(t('privacy'), contentHtml);
  setTimeout(() => {
    document.getElementById('privacy-export-data').onclick = async () => {
      try {
        const data = await api.exportUserData();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'sases_data.json'; a.click(); URL.revokeObjectURL(url);
        alert(t('export_data') + ' OK');
      } catch (e) { alert(t('save_failed') + ': ' + e.message); }
    };
    document.getElementById('privacy-delete-data').onclick = async () => {
      if (!confirm(t('delete_confirm') + '?')) return;
      try { await api.deleteUserCloudData(); alert(t('delete_cloud_data') + ' OK'); } catch (e) { alert(t('delete_failed') + ': ' + e.message); }
    };
  }, 100);
}

function openLanguageSettings() {
  const currentLang = localStorage.getItem('sases_lang') || 'zh';
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="lang-zh"><span class="menu-label">简体中文</span><span class="menu-check">${currentLang === 'zh' ? '✓' : ''}</span></div>
      <div class="me-menu-item" id="lang-en"><span class="menu-label">English</span><span class="menu-check">${currentLang === 'en' ? '✓' : ''}</span></div>
    </div>
  `;
  window.openSubpage(t('language_settings'), contentHtml);
  setTimeout(() => {
    document.getElementById('lang-zh').onclick = () => {
      localStorage.setItem('sases_lang', 'zh');
      alert(t('language_switched'));
      window.closeSubpage();
      // 重新渲染主页面
      if (typeof window.initMe === 'function') window.initMe();
    };
    document.getElementById('lang-en').onclick = () => {
      localStorage.setItem('sases_lang', 'en');
      alert(t('language_switched_en'));
      window.closeSubpage();
      if (typeof window.initMe === 'function') window.initMe();
    };
  }, 100);
}

function openAboutPage() {
  const contentHtml = `
    <div style="text-align:center;padding:30px 20px;">
      <div style="font-size:40px;margin-bottom:16px;">🌱</div>
      <div style="font-size:20px;font-weight:600;">SASES</div>
      <div style="color:#888;font-size:14px;margin-top:8px;">${t('version')} v0.12.1</div>
      <div style="color:#888;font-size:13px;margin-top:4px;">${t('privacy_tagline')}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="about-docs"><span class="menu-label">${t('docs')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="about-license"><span class="menu-label">${t('license')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="about-feedback"><span class="menu-label">${t('feedback')}</span><span class="menu-arrow">›</span></div>
    </div>
  `;
  window.openSubpage(t('about_sases'), contentHtml);
  setTimeout(() => {
    document.getElementById('about-docs').onclick = () => window.openSubpage(t('docs'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`);
    document.getElementById('about-license').onclick = () => window.openSubpage(t('license'), '<div class="subpage-placeholder">MIT License</div>');
    document.getElementById('about-feedback').onclick = () => window.openSubpage(t('feedback'), `<div class="subpage-placeholder">${t('coming_soon')}</div>`);
  }, 100);
}

// ==================== 授粉计划 ====================
function openPollinationPlan() {
  const contentHtml = `
    <div style="padding:20px 16px;background:#fff;border-radius:8px;margin-bottom:12px;">
      <h3 style="margin-bottom:8px;">🌱 ${t('pollination_plan')}</h3>
      <p style="color:#666;font-size:14px;line-height:1.6;">${t('pollination_desc') || '授粉是分享知识、获取积分的重要方式。'}</p>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('basic_value')}</span><span class="menu-value">+1</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('professional_value')}</span><span class="menu-value">+2</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('extreme_value')}</span><span class="menu-value">+3</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('local_bonus')}</span><span class="menu-value">+2</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('daily_personal_limit')}</span><span class="menu-value">100</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('bad_fruit_reward')}</span><span class="menu-value">+5 / ${t('daily')}50</span></div>
    </div>
    <div style="margin-top:12px;background:#f5f5f5;border-radius:8px;padding:12px;font-size:13px;color:#888;">
      ${t('group_pollination_rule')}
    </div>
  `;
  window.openSubpage(t('pollination_plan'), contentHtml, { showMore: false });
}

// 挂载到全局
window.openSettings = openSettings;