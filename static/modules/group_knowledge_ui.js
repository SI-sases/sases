window.openGroupKnowledge = async function(groupId) {
  let currentKeyword = '';

  const load = async () => {
    try {
      let url = '/group/' + groupId + '/knowledge';
      if (currentKeyword) url += '?keyword=' + encodeURIComponent(currentKeyword);
      const resp = await fetch(url, {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
      });
      const data = await resp.json();
      return data.docs || [];
    } catch (e) {
      return [];
    }
  };

  const renderList = (items) => {
    if (!items || items.length === 0) {
      return '<div class="subpage-placeholder">暂无知识条目</div>';
    }
    let html = '<div class="me-menu">';
    items.forEach(it => {
      const catLabel = { doc: '文档', faq: 'FAQ', meeting: '纪要', policy: '制度' }[it.category] || '文档';
      html += '<div class="me-menu-item gk-item" data-docid="' + it.id + '" style="flex-direction:column;align-items:flex-start;padding:12px;">';
      html += '<div style="width:100%;display:flex;align-items:center;justify-content:space-between;">';
      html += '<span style="font-size:14px;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:70%;">' + (it.title || '(无标题)') + '</span>';
      html += '<span class="menu-value" style="font-size:12px;color:#999;">' + catLabel + '</span>';
      html += '</div>';
      html += '<div style="font-size:12px;color:#999;margin-top:4px;width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + (it.content || '').substring(0, 50) + '</div>';
      html += '</div>';
    });
    html += '</div>';
    return html;
  };

  const bindItems = () => {
    document.querySelectorAll('.gk-item').forEach(el => {
      el.onclick = () => openGroupKnowledgeDetail(parseInt(el.dataset.docid), groupId);
    });
  };

  const items = await load();
  const html = `
    <div class="subpage-search-bar">
      <input type="text" id="gk-search" class="search-input" placeholder="搜索知识">
      <button class="search-btn" id="gk-search-btn">搜索</button>
    </div>
    <div id="gk-list">${renderList(items)}</div>
  `;
  window.openSubpage('群知识库', html, {
    showMore: false,
    returnAction: () => openGroupSettings(),
    rightBtn: {
      text: '添加',
      onclick: () => openGroupKnowledgeAdd(groupId)
    }
  });
  setTimeout(() => {
    const searchInput = document.getElementById('gk-search');
    const searchBtn = document.getElementById('gk-search-btn');
    const doSearch = async () => {
      currentKeyword = (searchInput || {}).value || '';
      const newItems = await load();
      document.getElementById('gk-list').innerHTML = renderList(newItems);
      bindItems();
    };
    if (searchBtn) searchBtn.onclick = doSearch;
    if (searchInput) searchInput.onkeydown = (e) => { if (e.key === 'Enter') doSearch(); };
    bindItems();
  }, 100);
};

window.openGroupKnowledgeDetail = async function(docId, groupId) {
  try {
    const resp = await fetch('/group/knowledge/' + docId, {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const d = await resp.json();
    if (d.error || d.detail) { alert('加载失败：' + (d.error || d.detail)); return; }
    const catLabel = { doc: '文档', faq: 'FAQ', meeting: '会议纪要', policy: '规章制度' }[d.category] || '文档';
    const html = `
      <div class="me-menu">
        <div class="me-menu-item" style="display:block;padding:12px;">
          <div style="font-size:16px;font-weight:600;color:#333;">${d.title || '(无标题)'}</div>
          <div style="font-size:12px;color:#999;margin-top:4px;">${catLabel} · ${d.created_at || ''}</div>
        </div>
      </div>
      <div class="me-menu">
        <div class="me-menu-item" style="display:block;padding:14px;font-size:14px;color:#333;line-height:1.7;white-space:pre-wrap;">${d.content || ''}</div>
      </div>
    `;
    window.openSubpage('知识详情', html, {
      showMore: false,
      returnAction: () => window.openGroupKnowledge(groupId)
    });
  } catch (e) { alert('网络错误：' + e.message); }
};

window.openGroupKnowledgeAdd = function(groupId) {
  const html = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">标题</span>
        <input id="gk-title" type="text" class="inline-input" placeholder="简短描述">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">分类</span>
        <select id="gk-category" class="inline-input">
          <option value="doc">文档</option>
          <option value="faq">FAQ</option>
          <option value="meeting">会议纪要</option>
          <option value="policy">规章制度</option>
        </select>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" style="display:block;padding:12px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">内容</div>
        <textarea id="gk-content" rows="6" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;"></textarea>
      </div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">标签</span>
        <input id="gk-tags" type="text" class="inline-input" placeholder="逗号分隔，可选">
      </div>
    </div>
    <button class="save-btn" id="gk-submit">保存</button>
  `;
  window.openSubpage('添加知识', html, {
    returnAction: () => window.openGroupKnowledge(groupId)
  });
  setTimeout(() => {
    const btn = document.getElementById('gk-submit');
    if (!btn) return;
    btn.onclick = async () => {
      const title = (document.getElementById('gk-title') || {}).value || '';
      const content = (document.getElementById('gk-content') || {}).value || '';
      const category = (document.getElementById('gk-category') || {}).value || 'doc';
      const tags = (document.getElementById('gk-tags') || {}).value || '';
      if (!content.trim()) { alert('内容不能为空'); return; }
      try {
        const resp = await fetch('/group/' + groupId + '/knowledge', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: title.trim(), content: content, category: category, tags: tags })
        });
        const data = await resp.json();
        if (data.error || data.detail) { alert('保存失败：' + (data.error || data.detail)); return; }
        alert('已保存');
        window.openGroupKnowledge(groupId);
      } catch (e) { alert('网络错误：' + e.message); }
    };
  }, 100);
};


// ======================================================================
// 【模块 6. 蜂群模式管理】
// ======================================================================

window.openSwarmConfig = async function(groupId) {
  let swarmEnabled = false;
  let sharedAgents = [];
  let allAgents = [];


window.openGroupKnowledge = openGroupKnowledge;
window.openGroupKnowledgeDetail = openGroupKnowledgeDetail;
window.openGroupKnowledgeAdd = openGroupKnowledgeAdd;
