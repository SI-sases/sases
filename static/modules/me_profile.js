// static/modules/me_profile.js
import { api } from './api.js';
import { t } from './i18n.js';

export async function openPersonalInfo() {
  let profile = null;
  try {
    profile = await api.getUserProfile();
  } catch (e) {
    console.warn('获取资料失败，使用本地缓存', e);
  }

  const username = profile?.username || localStorage.getItem('sases_username') || '用户';
  const sasesId = profile?.sases_id || localStorage.getItem('sases_sas_id') || '未设置';
  const gender = profile?.gender || localStorage.getItem('sases_gender') || '未设置';
  const region = profile?.region || localStorage.getItem('sases_region') || '未设置';
  const signature = profile?.signature || localStorage.getItem('sases_signature') || '未设置';

  const contentHtml = `
    <div class="personal-info-header">
      <div class="personal-info-avatar">${username.charAt(0).toUpperCase()}</div>
      <div class="personal-info-name">${username}</div>
      <div class="personal-info-id">SASES ID: ${sasesId}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="edit-nickname">
        <span class="menu-label">${t('nickname')}</span>
        <span class="menu-value">${username}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-sases-id">
        <span class="menu-label">${t('sases_id')}</span>
        <span class="menu-value">${sasesId}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-gender">
        <span class="menu-label">${t('gender')}</span>
        <span class="menu-value">${gender}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-region">
        <span class="menu-label">${t('region')}</span>
        <span class="menu-value">${region}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="edit-signature">
        <span class="menu-label">${t('signature')}</span>
        <span class="menu-value">${signature}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;

  window.openSubpage(t('personal_info'), contentHtml);

  setTimeout(() => {
    document.getElementById('edit-nickname').onclick = async () => {
      const newName = prompt(t('edit_nickname'), username);
      if (newName && newName.trim()) {
        try {
          await api.updateUserProfile({ username: newName.trim() });
          localStorage.setItem('sases_username', newName.trim());
          alert(t('update_success'));
          window.closeSubpage();
          location.reload();
        } catch (e) {
          alert(t('update_failed') + ': ' + e.message);
        }
      }
    };

    document.getElementById('edit-sases-id').onclick = () => alert(t('sases_id') + ' ' + t('unchangeable'));

    document.getElementById('edit-gender').onclick = async () => {
      const newGender = prompt(t('edit_gender'), gender);
      if (newGender) {
        try {
          await api.updateUserProfile({ gender: newGender });
          localStorage.setItem('sases_gender', newGender);
          alert(t('save_success_gender'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) {
          alert(t('save_failed') + ': ' + e.message);
        }
      }
    };

    document.getElementById('edit-region').onclick = async () => {
      const newRegion = prompt(t('edit_region'), region);
      if (newRegion) {
        try {
          await api.updateUserProfile({ region: newRegion });
          localStorage.setItem('sases_region', newRegion);
          alert(t('save_success_region'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) {
          alert(t('save_failed') + ': ' + e.message);
        }
      }
    };

    document.getElementById('edit-signature').onclick = async () => {
      const newSignature = prompt(t('edit_signature'), signature);
      if (newSignature) {
        try {
          await api.updateUserProfile({ signature: newSignature });
          localStorage.setItem('sases_signature', newSignature);
          alert(t('save_success_signature'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) {
          alert(t('save_failed') + ': ' + e.message);
        }
      }
    };
  }, 100);
}