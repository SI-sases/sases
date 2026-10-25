
function _showWxEditModal(title, defaultValue, isMultiline = false, options = null) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:flex-end;transition:opacity 0.3s;';
    
    const panel = document.createElement('div');
    panel.style.cssText = 'width:100%;background:#fff;border-radius:16px 16px 0 0;padding:20px;transform:translateY(100%);transition:transform 0.3s;box-sizing:border-box;';
    
    let inputHtml = '';
    if (options) {
      inputHtml = `<select id="_wx_edit_input" style="width:100%;font-size:16px;padding:12px;border:1px solid #eee;border-radius:8px;outline:none;background:#f9f9f9;">` + 
        options.map(o => `<option value="${o}" ${o===defaultValue?'selected':''}>${o}</option>`).join('') + `</select>`;
    } else if (isMultiline) {
      inputHtml = `<textarea id="_wx_edit_input" style="width:100%;height:100px;font-size:16px;padding:12px;border:1px solid #eee;border-radius:8px;outline:none;background:#f9f9f9;resize:none;">${defaultValue}</textarea>`;
    } else {
      inputHtml = `<input type="text" id="_wx_edit_input" value="${defaultValue}" style="width:100%;font-size:16px;padding:12px;border:1px solid #eee;border-radius:8px;outline:none;background:#f9f9f9;box-sizing:border-box;">`;
    }

    panel.innerHTML = `
      <div style="text-align:center;font-size:16px;font-weight:600;margin-bottom:20px;">${title}</div>
      ${inputHtml}
      <div style="display:flex;gap:12px;margin-top:24px;">
        <button id="_wx_edit_cancel" style="flex:1;padding:12px;border:none;border-radius:8px;background:#f2f2f2;color:#333;font-size:16px;">取消</button>
        <button id="_wx_edit_save" style="flex:1;padding:12px;border:none;border-radius:8px;background:#07c160;color:#fff;font-size:16px;">保存</button>
      </div>
    `;
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    
    setTimeout(() => { panel.style.transform = 'translateY(0)'; }, 10);

    const close = (val) => {
      panel.style.transform = 'translateY(100%)';
      overlay.style.opacity = '0';
      setTimeout(() => { overlay.remove(); resolve(val); }, 300);
    };

    document.getElementById('_wx_edit_cancel').onclick = () => close(null);
    document.getElementById('_wx_edit_save').onclick = () => close(document.getElementById('_wx_edit_input').value.trim());
  });
}

// static/modules/me.js
import { api } from './api.js';
import { t } from './me_i18n.js';

let initialized = false;

export function initMe() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('me-content');
  if (!container) return;

  const username = localStorage.getItem('sases_username') || '用户';
  const sasesId = localStorage.getItem('sases_sas_id') || t('not_set');
  const credits = localStorage.getItem('sases_credits_cache') || '0';

  container.innerHTML = `
    <div class="me-profile-card">
      <div class="me-profile-main" id="me-profile-main">
        <div class="me-avatar">${username.charAt(0).toUpperCase()}</div>
        <div class="me-info">
          <div class="me-name">${username}</div>
          <div class="me-id">${t('sases_id')}: ${sasesId}</div>
          <div class="me-credits">${t('seed_credits')}: ${credits}</div>
        </div>
        <div class="me-qrcode" id="me-qrcode">${t('qr_code')}</div>
        <div class="me-edit" id="me-edit-profile">✏️</div>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-models">
        <span class="menu-icon">🤖</span>
        <span class="menu-label">${t('model_management')}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item" id="menu-wallet">
        <span class="menu-icon">💰</span>
        <span class="menu-label">${t('wallet')}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-knowledge">
        <span class="menu-icon">📚</span>
        <span class="menu-label">个人知识库</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="menu-settings">
        <span class="menu-icon">⚙️</span>
        <span class="menu-label">${t('settings')}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>
  `;

  document.getElementById('me-profile-main').addEventListener('click', openPersonalInfo);
  document.getElementById('me-edit-profile').addEventListener('click', (e) => {
    e.stopPropagation();
    openPersonalInfo();
  });
  document.getElementById('me-qrcode').addEventListener('click', (e) => {
    e.stopPropagation();
    window.openSubpage(t('qr_code'), `
      <div style="text-align:center;padding:40px 20px;">
        <div style="font-size:16px;margin-bottom:20px;">${t('scan_add_friend')}</div>
        <div style="width:200px;height:200px;margin:0 auto;background:#fff;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:80px;">🔳</div>
        <div style="margin-top:16px;color:#888;font-size:13px;">${t('sases_id')}: ${sasesId}</div>
      </div>
    `);
  });

  document.getElementById('menu-models').addEventListener('click', () => {
    if (typeof window.openModelManagement === 'function') window.openModelManagement();
    else alert(t('model_management') + ' - ' + t('coming_soon'));
  });
  document.getElementById('menu-wallet').addEventListener('click', () => {
    if (typeof window.openWallet === 'function') window.openWallet();
    else alert(t('wallet') + ' - ' + t('coming_soon'));
  });
  const _el_knowledge = document.getElementById('menu-knowledge');
  if (_el_knowledge) _el_knowledge.addEventListener('click', openKnowledgeBase);
  const _el_contrib = document.getElementById('menu-contributions');
  if (_el_contrib) _el_contrib.addEventListener('click', openContributions);
  const _el_settings = document.getElementById('menu-settings');
  if (_el_settings) _el_settings.addEventListener('click', () => {
    if (typeof window.openSettings === 'function') window.openSettings();
    else alert(t('settings') + ' - ' + t('coming_soon'));
  });
  api.getBalance().then(data => {
    localStorage.setItem('sases_credits_cache', data.balance);
    const creditEl = document.querySelector('.me-credits');
    if (creditEl) creditEl.textContent = `${t('seed_credits')}: ${data.balance}`;
  }).catch(() => {});
}

// ==================== 个人资料 ====================
async function openPersonalInfo() {
  let profile = null;
  try {
    profile = await api.getUserProfile();
  } catch (e) {
    console.warn('获取资料失败', e);
  }

  const username = profile?.username || localStorage.getItem('sases_username') || '用户';
  const sasesId = profile?.sases_id || localStorage.getItem('sases_sas_id') || t('not_set');
  const gender = profile?.gender || localStorage.getItem('sases_gender') || t('not_set');
  const region = profile?.region || localStorage.getItem('sases_region') || t('not_set');
  const signature = profile?.signature || localStorage.getItem('sases_signature') || t('not_set');

  const contentHtml = `
    <div class="personal-info-header">
      <div class="personal-info-avatar">${username.charAt(0).toUpperCase()}</div>
      <div class="personal-info-name">${username}</div>
      <div class="personal-info-id">${t('sases_id')}: ${sasesId}</div>
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
      const newName = await _showWxEditModal(t('nickname'), username);
      if (newName && newName.trim()) {
        try {
          await api.updateUserProfile({ username: newName.trim() });
          localStorage.setItem('sases_username', newName.trim());
          alert(t('update_success'));
          window.closeSubpage();
          initMe();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
    document.getElementById('edit-sases-id').onclick = () => alert(t('sases_id') + ' ' + t('not_set'));
    document.getElementById('edit-gender').onclick = async () => {
      const newGender = await _showWxEditModal(t('gender'), gender, false, ['男', '女', '保密']);
      if (newGender) {
        try {
          await api.updateUserProfile({ gender: newGender });
          localStorage.setItem('sases_gender', newGender);
          alert(t('update_success'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
    document.getElementById('edit-region').onclick = async () => {
      const newRegion = await _showWxEditModal(t('region'), region);
      if (newRegion) {
        try {
          await api.updateUserProfile({ region: newRegion });
          localStorage.setItem('sases_region', newRegion);
          alert(t('update_success'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
    document.getElementById('edit-signature').onclick = async () => {
      const newSignature = await _showWxEditModal(t('signature'), signature, true);
      if (newSignature) {
        try {
          await api.updateUserProfile({ signature: newSignature });
          localStorage.setItem('sases_signature', newSignature);
          alert(t('update_success'));
          window.closeSubpage();
          openPersonalInfo();
        } catch (e) { alert(t('update_failed') + ': ' + e.message); }
      }
    };
  }, 100);
}

// ==================== 知识库 ====================
async function openKnowledgeBase() {

  let myDocsHtml = '';
  try {
    const token = localStorage.getItem('sases_token');
    const _r = await fetch('/knowledge/my-docs', { headers: { 'Authorization': 'Bearer ' + token } });
    const _d = await _r.json();
    const _docs = _d.documents || [];
    if (_docs.length === 0) {
      myDocsHtml = '<div class="subpage-placeholder">暂无个人文档。在会话里发 *1：标题：内容如下\\n正文 即可投喂。</div>';
    } else {
      myDocsHtml = '<div class="me-menu">';
      _docs.forEach(function(d, idx) {
        myDocsHtml += '<div class="me-menu-item" data-doc-index="' + idx + '" style="cursor:pointer;"><span class="menu-icon">📄</span><div class="menu-text"><div class="menu-title">' + (d.source_file || '未命名') + '</div><div class="menu-desc">' + (d.chunk_count || 0) + ' 个分片</div></div><span class="menu-arrow">›</span></div>';
      });
      myDocsHtml += '</div>';
      window._myDocsCache = _docs;
    }
  } catch (_e) {
    myDocsHtml = '<div class="subpage-placeholder">加载失败</div>';
  }
  window.openSubpage('个人知识库', myDocsHtml);

  setTimeout(function() {
    const _rows = document.querySelectorAll('#subpage-content [data-doc-index]');
    _rows.forEach(function(el) {
      const _idx = parseInt(el.getAttribute('data-doc-index'));
      const _doc = (window._myDocsCache || [])[_idx];
      if (!_doc) return;
      const _src = _doc.source_file;
      el.addEventListener('click', function() { openMyDoc(_src); });
      el.addEventListener('contextmenu', function(ev) { ev.preventDefault(); showDocContextMenu(ev.clientX, ev.clientY, _src); });
      let _lp = null;
      el.addEventListener('touchstart', function(ev) {
        const _t = ev.touches[0];
        _lp = setTimeout(function() { showDocContextMenu(_t.clientX, _t.clientY, _src); }, 800);
      }, { passive: true });
      el.addEventListener('touchend', function() { if (_lp) clearTimeout(_lp); });
      el.addEventListener('touchmove', function() { if (_lp) clearTimeout(_lp); });
    });
  }, 50);

  return;

  let knowledgeHtml = '';
  try {
    const data = await api.listKnowledge();
    const knowledge = data.knowledge || [];
    if (knowledge.length === 0) knowledgeHtml = `<div class="subpage-placeholder">${t('no_knowledge')}</div>`;
    else {
      knowledgeHtml = '<div class="me-menu">';
      knowledge.forEach(item => {
        const verifiedIcon = item.verified ? '✅' : '❌';
        knowledgeHtml += `<div class="me-menu-item"><span class="menu-icon">${verifiedIcon}</span><div class="menu-text"><div class="menu-title">${item.task}</div><div class="menu-desc">${item.solution.substring(0, 50)}...</div></div></div>`;
      });
      knowledgeHtml += '</div>';
    }
  } catch (e) { knowledgeHtml = `<div class="subpage-placeholder">${t('loading_failed')}</div>`; }
  window.openSubpage(t('knowledge_base'), knowledgeHtml);
}

async function openMyDoc(sourceFile) {
  try {
    const token = localStorage.getItem('sases_token');
    const url = '/knowledge/my-docs/' + encodeURIComponent(sourceFile);
    const r = await fetch(url, { headers: { 'Authorization': 'Bearer ' + token } });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    const content = d.content || '(空)';
    const html = '<div style="padding:12px;"><div style="font-size:13px;color:#888;margin-bottom:12px;">' + (d.source_file || '') + ' · ' + (d.chunk_count || 0) + ' 分片</div><pre style="white-space:pre-wrap;word-break:break-word;font-size:14px;line-height:1.6;font-family:inherit;">' + content.replace(/</g, '&lt;') + '</pre></div>';
    window.openSubpage(sourceFile, html, { returnAction: function() { openKnowledgeBase(); } });
  } catch (e) {
    alert('打开失败：' + e.message);
  }
}



// ==================== 我的贡献 ====================
async function openContributions() {
  let contribHtml = '';
  try {
    const data = await api.getCreditHistory(50);
    const history = data.history || [];
    if (history.length === 0) contribHtml = `<div class="subpage-placeholder">${t('no_history')}</div>`;
    else {
      contribHtml = '<div class="me-menu">';
      history.forEach(item => {
        const date = new Date(item.created_at).toLocaleString('zh-CN');
        contribHtml += `<div class="me-menu-item"><span class="menu-label">${item.action || t('my_contributions')}</span><span class="menu-value">${item.points > 0 ? '+' : ''}${item.points}</span></div><div style="padding:0 12px 8px;font-size:12px;color:#999;">${date} · ${item.detail || ''}</div>`;
      });
      contribHtml += '</div>';
    }
  } catch (e) { contribHtml = `<div class="subpage-placeholder">${t('loading_failed')}</div>`; }
  window.openSubpage(t('my_contributions'), contribHtml);
}

// 导出全局（供其他模块调用或挂载）
window.openKnowledgeBase = openKnowledgeBase;
window.openContributions = openContributions;


async function deleteDocAndRefresh(sourceFile) {
  try {
    await api.deleteMyDoc(sourceFile);
    alert('已删除');
    openKnowledgeBase();
  } catch (e) {
    alert('删除失败：' + e.message);
  }
}


function showDocContextMenu(x, y, sourceFile) {
  const _old = document.getElementById('doc-context-menu');
  if (_old) _old.remove();
  const _menu = document.createElement('div');
  _menu.id = 'doc-context-menu';
  _menu.className = 'message-context-menu';
  _menu.style.position = 'fixed';
  _menu.style.left = x + 'px';
  _menu.style.top = y + 'px';
  _menu.style.display = 'block';
  _menu.innerHTML = '<div class="context-menu-item" data-action="open">打开文档</div>' + '<div class="context-menu-item" data-action="delete" style="color:#e64340;">删除</div>';
  document.body.appendChild(_menu);
  _menu.querySelector('[data-action="open"]').addEventListener('click', function() {
    _menu.remove();
    openMyDoc(sourceFile);
  });
  _menu.querySelector('[data-action="delete"]').addEventListener('click', function() {
    _menu.remove();
    if (confirm('确定删除《' + sourceFile + '》？删除后不可恢复。')) {
      deleteDocAndRefresh(sourceFile);
    }
  });
  setTimeout(function() {
    const _close = function(ev) {
      if (!_menu.contains(ev.target)) {
        _menu.remove();
        document.removeEventListener('click', _close);
      }
    };
    document.addEventListener('click', _close);
  }, 50);
}

// ====== 安全接管关于SASES ======
document.addEventListener('click', function(e) {
    var target = e.target;
    var isAbout = false;
    while (target && target !== document) {
        if (target.innerText && target.innerText.trim() === '关于 SASES') {
            isAbout = true;
            break;
        }
        target = target.parentNode;
    }
    if (isAbout && typeof window.openSubpage === 'function') {
        var html = '<div style="padding: 30px 20px; text-align: center; color: #333;">' +
            '<h2 style="color: #007aff; margin-bottom: 5px;">SASES</h2>' +
            '<p style="color: #888; font-size: 14px; margin-bottom: 30px;">v1.0.0-Release</p>' +
            '<div style="text-align: left; background: #fff; padding: 15px; border-radius: 8px; line-height: 1.8; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">' +
                '<p><strong>开源协议：</strong>MIT License</p>' +
                '<p><strong>项目地址：</strong><a href="https://github.com/SI-sases/sases" target="_blank" style="color: #007aff; text-decoration: none;">github.com/SI-sases/sases</a></p>' +
                '<p><strong>商业化说明：</strong>个人学习、研究及企业内部使用完全免费。如需作为商业产品对外提供服务，必须获得官方商业授权。</p>' +
            '</div>' +
        '</div>';
        window.openSubpage('关于 SASES', html, { returnAction: function() { if (window.closeSubpage) window.closeSubpage(); } });
    }
}, true);
