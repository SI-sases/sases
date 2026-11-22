import { t } from './i18n.js';

window.openPublishTaskDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">${t('groupTask.titleLabel')}</div>
        <input id="pt-title" type="text" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;" placeholder="请输入标题">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务描述</div>
        <textarea id="pt-desc" rows="3" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;resize:vertical;" placeholder="可选"></textarea>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务类型</div>
        <select id="pt-category" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
          <option value="text">文本</option>
          <option value="image">图片</option>
          <option value="code">代码</option>
          <option value="creative">创意</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">质押积分（最少 10）</div>
        <input id="pt-reward" type="number" value="10" min="10" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-bottom:20px;font-size:12px;color:#874d00;line-height:1.6;">
        ⚠️ 任务完成后，<b>95%</b> 给被选中的方案提交者，<b>5%</b> 进入群积分池。
      </div>
      <button id="pt-submit" style="width:100%;padding:12px;background:#07c160;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">发布任务</button>
    </div>
  `;
  window.openSubpage(t('groupTask.publishTitle'), html);
  setTimeout(function() {
    const btn = document.getElementById('pt-submit');
    if (!btn) return;
    btn.onclick = function() {
      const title = (document.getElementById('pt-title') || {}).value || '';
      const desc = (document.getElementById('pt-desc') || {}).value || '';
      const category = (document.getElementById('pt-category') || {}).value || 'text';
      const rewardStr = (document.getElementById('pt-reward') || {}).value || '0';
      if (!title.trim()) { alert(t('groupTask.titleRequired')); return; }
      const reward = parseFloat(rewardStr);
      if (isNaN(reward) || reward < 10) { alert(t('groupTask.rewardMin')); return; }
      fetch('/group/' + groupId + '/tasks/publish', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), description: desc, category: category, reward: reward })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert(t('gt_publish_failed') + '：' + (data.error || data.detail)); return; }
        alert(t('groupTask.published'));
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        if (typeof loadGroupMessages === 'function') loadGroupMessages();
      }).catch(e => alert(t('gt_network_error') + '：' + e.message));
    };
  }, 300);
};


window.openTaskDetail = function(taskId) {
  fetch('/group/tasks/' + taskId, {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
  }).then(r => r.json()).then(task => {
    if (task.error || task.detail) { alert(t('gt_load_failed') + '：' + (task.error || task.detail)); return; }
    const subs = task.submissions || [];
    const myId = parseInt(localStorage.getItem('sases_user_id') || '0');
    const isOwner = task.created_by === myId;
    const isOpen = task.status === 'open';
    let subHtml = '';
    if (subs.length === 0) {
      subHtml = '<div style="text-align:center;color:#999;padding:30px 0;">' + t('gt_no_submissions') + '</div>';
    } else {
      subs.forEach(s => {
        subHtml += '<div style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;">';
        subHtml += '<div style="font-size:13px;color:#666;margin-bottom:6px;">' + (s.submitter_name || t('gt_anonymous')) + '</div>';
        subHtml += '<div style="font-size:14px;color:#333;word-break:break-all;white-space:pre-wrap;margin-bottom:8px;">' + (s.content || '') + '</div>';
        if (isOwner && isOpen) {
          subHtml += '<button class="pick-sub-btn" data-sid="' + s.id + '" style="padding:6px 14px;background:#07c160;color:#fff;border:none;border-radius:4px;font-size:13px;cursor:pointer;">' + t('gt_pick') + '</button>';
        }
        subHtml += '</div>';
      });
    }
    let actionHtml = '';
    if (!isOwner && isOpen) {
      actionHtml = '<button id="td-submit-btn" style="width:100%;padding:12px;background:#07c160;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;margin-top:16px;">' + t('gt_submit_plan') + '</button>';
    } else if (isOwner && isOpen && subs.length > 0) {
      actionHtml = '<div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-top:16px;font-size:12px;color:#874d00;">' + t('gt_pick_hint') + '</div>';
    }
    const html = `
      <div style="padding:16px;">
        <div style="font-size:18px;font-weight:600;margin-bottom:8px;">${task.title || t('gt_untitled')}</div>
        <div style="font-size:13px;color:#666;margin-bottom:12px;">
          质押 ${task.reward_credits || 0} 积分 · 状态：${isOpen ? t('gt_in_progress') : task.status}
        </div>
        <div style="background:#f8f8f8;border-radius:8px;padding:12px;margin-bottom:20px;font-size:14px;color:#333;white-space:pre-wrap;">${task.description || t('gt_no_desc')}</div>
        <div style="font-size:15px;font-weight:600;margin-bottom:10px;">提交列表 (${subs.length})</div>
        ${subHtml}
        ${actionHtml}
      </div>
    `;
    window.openSubpage(t('gt_detail_title'), html);
    setTimeout(function() {
      const submitBtn = document.getElementById('td-submit-btn');
      if (submitBtn) {
        submitBtn.onclick = function() {
          const content = prompt(t('gt_plan_prompt'));
          if (!content) return;
          fetch('/group/tasks/' + taskId + '/submit', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content, content_type: 'text' })
          }).then(r => r.json()).then(data => {
            if (data.error || data.detail) { alert(t('gt_submit_failed') + (data.error || data.detail)); return; }
            alert(t('gt_submit_ok'));
            window.openTaskDetail(taskId);
          }).catch(e => alert('网络错误：' + e.message));
        };
      }
      document.querySelectorAll('.pick-sub-btn').forEach(btn => {
        btn.onclick = function() {
          const sid = btn.dataset.sid;
          if (!confirm(t('gt_pick_confirm'))) return;
          fetch('/group/tasks/' + taskId + '/select', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ submission_id: parseInt(sid) })
          }).then(r => r.json()).then(data => {
            if (data.error || data.detail) { alert(t('gt_pick_failed') + (data.error || data.detail)); return; }
            alert(t('gt_picked') + data.winner_gets + ' / +' + data.pool_gets);
            window.openTaskDetail(taskId);
          }).catch(e => alert('网络错误：' + e.message));
        };
      });
    }, 100);
  }).catch(e => alert('网络错误：' + e.message));
};
