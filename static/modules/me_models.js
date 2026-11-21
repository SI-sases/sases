// static/modules/me_models.js
import { api } from './api.js';
import { t } from './me_i18n.js';

// ==================== 模型管理 ====================
export async function openModelManagement(returnAction = null) {
  let modelsHtml = '';
  try {
    const data = await api.listModels();
    const models = data.models || [];
    window.__sasesModelsCache = {};
    models.forEach(m => { window.__sasesModelsCache[m.id] = m; });
    if (models.length === 0) {
      modelsHtml = `<div class="subpage-placeholder">${t('no_models')}</div>`;
    } else {
      modelsHtml = '<div class="me-menu">';
      models.forEach(m => {
        const icon = m.model_type === 'local' ? '🖥️' : '🔑';
        const detail = m.model_type === 'local' ? `${m.model_name} @ ${m.node_url}` : `${m.provider}`;
        const bonusTag = m.model_type === 'local' ? ' <span style="color:green;font-size:12px;">授粉+2</span>' : '';
        const shareText = m.is_shared ? t('shared') : t('not_shared');
        modelsHtml += `
          <div class="me-menu-item model-item" data-model-id="${m.id}" data-is-shared="${m.is_shared}" data-visibility="${m.visibility}" data-price="${m.price}">
            <span>${icon}</span>
            <div class="model-info">
              <div>${m.name}${bonusTag}</div>
              <div class="model-detail">${detail}</div>
              <div class="model-id-display" style="font-size:12px;color:#999;">ID: ${m.id}</div>
              <div class="model-share-info" style="font-size:12px;color:#007aff;">${shareText} · ${m.visibility} · ${m.price}${t('price_unit')}</div>
            </div>
            <button class="edit-share-btn" data-model-id="${m.id}">${t('share_settings')}</button>
            <button class="edit-model-btn" data-model-id="${m.id}" style="margin-left:4px;">编辑</button>
            <button class="delete-model-btn" data-model-id="${m.id}" style="margin-left:4px;color:#d93025;">删除</button>
          </div>
        `;
      });
      modelsHtml += '</div>';
    }
  } catch (e) {
    modelsHtml = `<div class="subpage-placeholder">${t('loading_failed') || '加载失败'}: ${e.message}</div>`;
  }

  const contentHtml = `
    <div style="background:#fff;border-radius:8px;padding:12px;margin-bottom:12px;border-left:4px solid #007aff;">
      <div style="font-weight:500;margin-bottom:6px;">🧭 ${t('config_guide_title')}</div>
      <div style="font-size:13px;color:#666;line-height:1.5;">${t('config_guide_content')}</div>
    </div>
    <div style="background:#fff;border-radius:8px;padding:12px;margin-bottom:12px;border-left:4px solid #ff9500;">
      <div style="font-weight:500;margin-bottom:6px;">⚠️ ${t('risk_title')}</div>
      <div style="font-size:13px;color:#666;line-height:1.5;">${t('risk_content')}</div>
    </div>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <button id="add-api-key" style="flex:1;padding:10px;background:#007aff;color:#fff;border:none;border-radius:6px;">${t('add_api_key')}</button>
      <button id="add-local-model" style="flex:1;padding:10px;background:#34c759;color:#fff;border:none;border-radius:6px;">${t('add_local_model')}</button>
    </div>
    ${modelsHtml}
  `;
  window.openSubpage(t('model_management'), contentHtml, { showMore: false, returnAction: returnAction || (() => window.activateMainView('me')) });

  setTimeout(() => {
    const addApiKeyBtn = document.getElementById('add-api-key');
    const addLocalModelBtn = document.getElementById('add-local-model');
    if (addApiKeyBtn) addApiKeyBtn.onclick = openAddApiKeyForm;
    if (addLocalModelBtn) addLocalModelBtn.onclick = openAddLocalModelForm;

    document.querySelectorAll('.edit-share-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const modelId = btn.dataset.modelId;
        const modelItem = btn.closest('.model-item');
        const isShared = modelItem.dataset.isShared === '1' ? 1 : 0;
        const visibility = modelItem.dataset.visibility;
        const price = parseFloat(modelItem.dataset.price);
        openShareSettings(modelId, isShared, visibility, isNaN(price) ? 0 : price);
      };
    });

    document.querySelectorAll('.edit-model-btn').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const id = btn.dataset.modelId;
        const data = window.__sasesModelsCache && window.__sasesModelsCache[id];
        openModelEditForm(id, data || {});
      };
    });

    document.querySelectorAll('.delete-model-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.dataset.modelId;
        try {
          const rr = await api.getModelRefs(id);
          const refs = (rr && rr.refs) || {};
          const n = refs.conversations || 0;
          if (!confirm('删除后将同时删除 ' + n + ' 个会话，且不可恢复。确定删除？')) return;
          await api.deleteModel(id);
          openModelManagement();
        } catch (err) {
          alert('删除失败：' + (err.message || err));
        }
      };
    });
  }, 100);
}

function openAddApiKeyForm() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('name')}</span>
        <input type="text" id="api-name-input" class="inline-input" placeholder="${t('name')}">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('provider')}</span>
        <select id="api-provider-input" class="inline-input">
          <option value="deepseek">DeepSeek (deepseek)</option>
          <option value="openai">OpenAI (openai)</option>
          <option value="moonshot">Moonshot/Kimi (moonshot)</option>
          <option value="claude">Claude/Anthropic (claude)</option>
          <option value="zhipu">智谱 GLM (zhipu)</option>
          <option value="qwen">阿里通义千问 (qwen)</option>
          <option value="custom">自定义 (custom)</option>
        </select>
        <input type="text" id="api-provider-custom-input" class="inline-input" placeholder="custom provider" style="display:none;">

        
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('api_key')}</span>
        <input type="password" id="api-key-input" class="inline-input" placeholder="sk-...">
      </div>
    </div>
    <button class="save-btn" id="save-api-key">${t('save')}</button>
  `;
  window.openSubpage(t('add_api_key'), contentHtml);

  setTimeout(() => {
    
      const _sel = document.getElementById('api-provider-input');
      const _cus = document.getElementById('api-provider-custom-input');
      if (_sel && _cus) {
        _sel.addEventListener('change', function() {
          _cus.style.display = (this.value === 'custom') ? 'block' : 'none';
        });
      }

      document.getElementById('save-api-key').onclick = async () => {
      const name = document.getElementById('api-name-input').value.trim();
      let provider = document.getElementById('api-provider-input').value.trim();
      if (provider === 'custom') {
        provider = document.getElementById('api-provider-custom-input').value.trim();
      }
      const api_key = document.getElementById('api-key-input').value.trim();
      if (!name || !provider || !api_key) { alert(t('enter_all')); return; }
      try {
        await api.addApiKey({ name, provider, api_key, priority: 1 });
        alert(t('add_success'));
        // 上报新手引导动作：创建智能体（Day 2）
        if (typeof window.onboarding?.report === 'function') {
          window.onboarding.report('create_agent');
        }
        window.closeSubpage();
        openModelManagement();
      } catch (e) { alert(t('add_failed') + ': ' + e.message); }
    };
  }, 100);
}

function openAddLocalModelForm() {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('name')}</span>
        <input type="text" id="local-name-input" class="inline-input" placeholder="${t('name')}">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('node_url')}</span>
        <input type="text" id="local-url-input" class="inline-input" placeholder="http://192.168.1.100:11434">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('model_name')}</span>
        <input type="text" id="local-model-input" class="inline-input" placeholder="tinyllama">
      </div>
    </div>
    <button class="save-btn" id="save-local-model">${t('save')}</button>
  `;
  window.openSubpage(t('add_local_model'), contentHtml);

  setTimeout(() => {
    document.getElementById('save-local-model').onclick = async () => {
      const name = document.getElementById('local-name-input').value.trim();
      const node_url = document.getElementById('local-url-input').value.trim();
      const model_name = document.getElementById('local-model-input').value.trim();
      if (!name || !node_url || !model_name) { alert(t('enter_all')); return; }
      try {
        await api.addLocalModel({ name, node_url, model_name });
        alert(t('add_success'));
        // 上报新手引导动作：创建智能体（Day 2）
        if (typeof window.onboarding?.report === 'function') {
          window.onboarding.report('create_agent');
        }
        window.closeSubpage();
        openModelManagement();
      } catch (e) { alert(t('add_failed') + ': ' + e.message); }
    };
  }, 100);
}

function openModelEditForm(modelId, m) {
  const isLocal = m.model_type === 'local';
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">名称</span>
        <input type="text" id="edit-model-name" class="inline-input" value="${String(m.name || '').replace(/"/g, '&quot;')}"></div>
      ${isLocal ? `
      <div class="me-menu-item"><span class="menu-label">节点地址</span>
        <input type="text" id="edit-node-url" class="inline-input" value="${String(m.node_url || '').replace(/"/g, '&quot;')}"></div>
      <div class="me-menu-item"><span class="menu-label">模型名</span>
        <input type="text" id="edit-model-name-field" class="inline-input" value="${String(m.model_name || '').replace(/"/g, '&quot;')}"></div>
      ` : `
      <div class="me-menu-item"><span class="menu-label">Provider</span>
        <input type="text" id="edit-provider" class="inline-input" value="${String(m.provider || '').replace(/"/g, '&quot;')}"></div>
      <div class="me-menu-item"><span class="menu-label">API Key</span>
        <input type="password" id="edit-api-key" class="inline-input" placeholder="留空表示不修改"></div>
      `}
    </div>
    <button class="save-btn" id="save-model-edit">保存</button>
  `;
  window.openSubpage('编辑智能体', contentHtml);
  setTimeout(() => {
    const btn = document.getElementById('save-model-edit');
    if (!btn) return;
    btn.onclick = async () => {
      const payload = { name: (document.getElementById('edit-model-name').value || '').trim() };
      if (isLocal) {
        payload.node_url = (document.getElementById('edit-node-url').value || '').trim();
        payload.model_name = (document.getElementById('edit-model-name-field').value || '').trim();
      } else {
        payload.provider = (document.getElementById('edit-provider').value || '').trim();
        const k = (document.getElementById('edit-api-key').value || '').trim();
        if (k) payload.api_key = k;
      }
      try {
        await api.updateModel(modelId, payload);
        window.closeSubpage();
        openModelManagement();
      } catch (e) {
        alert('保存失败：' + (e.message || e));
      }
    };
  }, 100);
}

function openShareSettings(modelId, isShared, visibility, price) {
  const safePrice = isNaN(price) ? 0 : price;
  const visibilityMap = { 'private': t('private'), 'friends': t('friends'), 'public': t('public') };
  const currentVisibilityText = visibilityMap[visibility] || visibility;

  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('allow_share')}</span>
        <label class="switch">
          <input type="checkbox" id="share-enabled" ${isShared ? 'checked' : ''}>
          <span class="slider"></span>
        </label>
      </div>
      <div class="me-menu-item" id="share-visibility-selector">
        <span class="menu-label">${t('visibility')}</span>
        <span class="menu-value" id="share-visibility-text">${currentVisibilityText}</span>
        <span class="menu-arrow">›</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('call_price')}</span>
        <input type="number" id="share-price" class="inline-input" value="${safePrice}" min="0" step="0.5">
        <span class="menu-unit">${t('price_unit')}</span>
      </div>
    </div>
    <button class="save-btn" id="save-share-settings">${t('save')}</button>
  `;
  window.openSubpage(t('share_settings'), contentHtml, { showMore: false });

  setTimeout(() => {
    document.getElementById('share-visibility-selector').onclick = () => {
      const optionsHtml = `<div class="me-menu"><div class="me-menu-item visibility-option" data-value="private">${t('private')}</div><div class="me-menu-item visibility-option" data-value="friends">${t('friends')}</div><div class="me-menu-item visibility-option" data-value="public">${t('public')}</div></div>`;
      window.openSubpage(t('visibility'), optionsHtml, { showMore: false });
      setTimeout(() => {
        document.querySelectorAll('.visibility-option').forEach(opt => {
          opt.onclick = () => {
            const newValue = opt.dataset.value;
            document.getElementById('share-visibility-text').textContent = opt.textContent;
            document.getElementById('share-visibility-selector').dataset.value = newValue;
            window.closeSubpage();
          };
        });
      }, 100);
    };

    document.getElementById('save-share-settings').onclick = async () => {
      const enabled = document.getElementById('share-enabled').checked ? 1 : 0;
      const vis = document.getElementById('share-visibility-selector').dataset.value || 'private';
      const priceVal = parseFloat(document.getElementById('share-price').value) || 0;
      try {
        await api.updateModelShare(modelId, { is_shared: enabled, visibility: vis, price: priceVal });
        alert(t('save_success'));
        window.closeSubpage();
        openModelManagement();
      } catch (e) { alert(t('save_failed') + ': ' + e.message); }
    };
  }, 100);
}

window.openModelManagement = openModelManagement;