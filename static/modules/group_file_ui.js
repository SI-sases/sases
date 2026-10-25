// static/modules/group_file_ui.js
// 群文件（从 group_chat.js 迁出）

export async function openGroupFiles(groupId) {
  let files = [];
  try {
    const resp = await fetch('/group/' + groupId + '/files', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    if (data.error || data.detail) { alert('加载失败：' + (data.error || data.detail)); return; }
    files = data.files || [];
  } catch (e) { alert('网络错误：' + e.message); return; }

  const fmtSize = (s) => {
    const n = parseInt(s) || 0;
    if (n < 1024) return n + 'B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + 'KB';
    return (n / 1024 / 1024).toFixed(1) + 'MB';
  };

  let listHtml = '';
  if (files.length === 0) {
    listHtml = '<div class="subpage-placeholder">暂无群文件</div>';
  } else {
    files.forEach(f => {
      listHtml += '<div class="me-menu-item group-file-item" data-url="' + f.url + '" style="cursor:pointer;">';
      listHtml += '<div style="flex:1;min-width:0;">';
      listHtml += '<div style="font-size:14px;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">📎 ' + (f.name || '文件') + '</div>';
      listHtml += '<div style="font-size:12px;color:#999;margin-top:2px;">' + (f.sender_name || '群友') + ' · ' + fmtSize(f.size) + '</div>';
      listHtml += '</div>';
      listHtml += '<span class="menu-arrow">›</span>';
      listHtml += '</div>';
    });
  }

  const html = '<div class="me-menu">' + listHtml + '</div>';
  window.openSubpage('群文件', html, {
    showMore: false,
    returnAction: () => window.openGroupSettings && window.openGroupSettings()
  });

  setTimeout(() => {
    document.querySelectorAll('.group-file-item').forEach(el => {
      el.onclick = () => window.open(el.dataset.url, '_blank');
    });
  }, 100);
}

window.openGroupFiles = openGroupFiles;
