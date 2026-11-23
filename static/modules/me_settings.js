// static/modules/me_settings.js
import { api } from './api.js';
import { t, setLang, getLang } from './i18n.js';
import { setNodeBundle, clearNodeIdentity, getNodeId, getNodeProfile, refreshNodeManifest, applyCreator } from './node_identity_client.js';

// 语言选择用全局函数 + 内联 onclick，避免子页面重绘后事件监听丢失
// 注意：不要在这里 location.reload()。整页刷新会打断 openSettings 的 setTimeout 绑定、
// 丢失当前所在 tab 与子页栈，且 me.js 的 initialized 缓存会让文案不更新。
// 正确做法：setLang() 广播 langchange，由各模块监听后原地重绘。
window.__sasesPickLang = function (lang) {
  if (lang === getLang()) {
    if (typeof window.closeSubpage === 'function') window.closeSubpage();
    return;
  }
  setLang(lang);
  if (typeof window.closeSubpage === 'function') window.closeSubpage();
};
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
      <div class="me-menu-item" id="set-node"><span class="menu-label">${t('node_identity')}</span><span class="menu-value">${getNodeProfile() || t('node_not_set')}</span><span class="menu-arrow">›</span></div>
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
    document.getElementById('set-node').onclick = openNodeIdentity;
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
  const username = localStorage.getItem('sases_username') || t('mp_user');
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
  const currentLang = getLang();
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item" id="lang-zh" data-lang-choice="zh" onclick="window.__sasesPickLang('zh')"><span class="menu-label">${t('ms_zh')}</span><span class="menu-check">${currentLang === 'zh' ? '✓' : ''}</span></div>
      <div class="me-menu-item" id="lang-en" data-lang-choice="en" onclick="window.__sasesPickLang('en')"><span class="menu-label">English</span><span class="menu-check">${currentLang === 'en' ? '✓' : ''}</span></div>
    </div>
  `;
  window.openSubpage(t('language_settings'), contentHtml);
}

function openAboutPage() {
  const contentHtml = '<div style="padding: 30px 20px; text-align: center; color: #333;">' +
    '<div style="font-size:50px; margin-bottom: 10px;">🌱</div>' +
    '<h2 style="color: #007aff; margin-bottom: 5px;">SASES</h2>' +
    '<p style="color: #888; font-size: 14px; margin-bottom: 30px;">v1.0.0-Release</p>' +
    '<div style="text-align: left; background: #fff; padding: 15px; border-radius: 8px; line-height: 1.8; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">' +
        '<p><strong>' + t('ms_license') + ':</strong>MIT License</p>' +
        '<p><strong>' + t('ms_project_url') + ':</strong><a href="https://github.com/SI-sases/sases" target="_blank" style="color: #007aff; text-decoration: none;">github.com/SI-sases/sases</a></p>' +
    '</div>' +
  '</div>';
  window.openSubpage(t('about_sases'), contentHtml);
}

// ==================== 授粉计划 ====================
function openPollinationPlan() {
  const contentHtml = `
    <div style="padding:20px 16px;background:#fff;border-radius:8px;margin-bottom:12px;">
      <h3 style="margin-bottom:8px;">🌱 ${t('pollination_plan')}</h3>
      <p style="color:#666;font-size:14px;line-height:1.6;">${t('ms_pollination_desc')}</p>
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

// ==================== 节点身份 ====================
function openNodeIdentity() {
  const nodeId = getNodeId();
  const profile = getNodeProfile();
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">node_id</span><span class="menu-value">${nodeId || t('node_not_set')}</span></div>
      <div class="me-menu-item"><span class="menu-label">profile</span><span class="menu-value">${profile || t('node_not_set')}</span></div>
    </div>
    <div style="padding:12px;background:#f5f5f5;border-radius:8px;font-size:12px;color:#666;line-height:1.6;">
      ${t('node_import_hint')}
    </div>
    <div style="padding:12px 0;">
      <input type="file" id="node-bundle-file" accept=".json,application/json" style="width:100%;">
    </div>
    <button class="save-btn" id="node-import" style="width:100%;">${t('node_import')}</button>
  `;
  window.openSubpage(t('node_identity'), contentHtml, { showMore: false });
  setTimeout(() => {
    const importBtn = document.getElementById('node-import');
    if (importBtn) importBtn.onclick = async () => {
      const input = document.getElementById('node-bundle-file');
      const file = input && input.files && input.files[0];
      if (!file) { alert(t('node_import_failed')); return; }
      try {
        const bundle = JSON.parse(await file.text());
        setNodeBundle(bundle);
        await refreshNodeManifest(localStorage.getItem('sases_token'));
        alert(t('node_import_ok'));
        window.closeSubpage();
        openSettings();
      } catch (e) {
        alert(t('node_import_failed') + ': ' + e.message);
      }
    };
    if (nodeId) {
      const clearBtn = document.createElement('button');
      clearBtn.className = 'save-btn';
      clearBtn.style.cssText = 'width:100%;margin-top:8px;background:#ff3b30;';
      clearBtn.textContent = t('node_clear');
      clearBtn.onclick = () => {
        clearNodeIdentity();
        alert(t('node_clear_ok'));
        window.closeSubpage();
        openSettings();
      };
      importBtn.parentNode.appendChild(clearBtn);

      if (profile === 'edge') {
        const applyBtn = document.createElement('button');
        applyBtn.className = 'save-btn';
        applyBtn.style.cssText = 'width:100%;margin-top:8px;background:#34c759;';
        applyBtn.textContent = t('node_apply_creator');
        applyBtn.onclick = async () => {
          const note = prompt(t('node_apply_creator')) || '';
          try {
            await applyCreator(nodeId, note);
            alert(t('node_apply_sent'));
          } catch (e) {
            alert(t('node_apply_failed') + ': ' + e.message);
          }
        };
        importBtn.parentNode.appendChild(applyBtn);
      }
    }
  }, 100);
}

// 挂载到全局
window.openSettings = openSettings;