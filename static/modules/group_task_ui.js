window.openPublishTaskDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">任务标题</div>
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
  window.openSubpage('发布任务', html);
  setTimeout(function() {
    const btn = document.getElementById('pt-submit');
    if (!btn) return;
    btn.onclick = function() {
      const title = (document.getElementById('pt-title') || {}).value || '';
      const desc = (document.getElementById('pt-desc') || {}).value || '';
      const category = (document.getElementById('pt-category') || {}).value || 'text';
      const rewardStr = (document.getElementById('pt-reward') || {}).value || '0';
      if (!title.trim()) { alert('请输入标题'); return; }
      const reward = parseFloat(rewardStr);
      if (isNaN(reward) || reward < 10) { alert('质押积分最少 10'); return; }
      fetch('/group/' + groupId + '/tasks/publish', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), description: desc, category: category, reward: reward })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert('发布失败：' + (data.error || data.detail)); return; }
        alert('任务已发布');
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        if (typeof loadGroupMessages === 'function') loadGroupMessages();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
};


window.openTaskDetail = function(taskId) {
  fetch('/group/tasks/' + taskId, {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
  }).then(r => r.json()).then(task => {
    if (task.error || task.detail) { alert('加载失败：' + (task.error || task.detail)); return; }
    const subs = task.submissions || [];
    const myId = parseInt(localStorage.getItem('sases_user_id') || '0');
    const isOwner = task.created_by === myId;
    const isOpen = task.status === 'open';
    let subHtml = '';
    if (subs.length === 0) {
      subHtml = '<div style="text-align:center;color:#999;padding:30px 0;">暂无提交</div>';
    } else {
      subs.forEach(s => {
        subHtml += '<div style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;">';
        subHtml += '<div style="font-size:13px;color:#666;margin-bottom:6px;">' + (s.submitter_name || '匿名') + '</div>';
        subHtml += '<div style="font-size:14px;color:#333;word-break:break-all;white-space:pre-wrap;margin-bottom:8px;">' + (s.content || '') + '</div>';
        if (isOwner && isOpen) {
          subHtml += '<button class="pick-sub-btn" data-sid="' + s.id + '" style="padding:6px 14px;background:#07c160;color:#fff;border:none;border-radius:4px;font-size:13px;cursor:pointer;">选择此方案</button>';
        }
        subHtml += '</div>';
      });
    }
    let actionHtml = '';
    if (!isOwner && isOpen) {
      actionHtml = '<button id="td-submit-btn" style="width:100%;padding:12px;background:#07c160;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;margin-top:16px;">提交方案</button>';
    } else if (isOwner && isOpen && subs.length > 0) {
      actionHtml = '<div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-top:16px;font-size:12px;color:#874d00;">请在提交列表中点击"选择此方案"，未选择将超时退款。</div>';
    }
    const html = `
      <div style="padding:16px;">
        <div style="font-size:18px;font-weight:600;margin-bottom:8px;">${task.title || '未命名任务'}</div>
        <div style="font-size:13px;color:#666;margin-bottom:12px;">
          质押 ${task.reward_credits || 0} 积分 · 状态：${isOpen ? '进行中' : task.status}
        </div>
        <div style="background:#f8f8f8;border-radius:8px;padding:12px;margin-bottom:20px;font-size:14px;color:#333;white-space:pre-wrap;">${task.description || '（无描述）'}</div>
        <div style="font-size:15px;font-weight:600;margin-bottom:10px;">提交列表 (${subs.length})</div>
        ${subHtml}
        ${actionHtml}
      </div>
    `;
    window.openSubpage('任务详情', html);
    setTimeout(function() {
      const submitBtn = document.getElementById('td-submit-btn');
      if (submitBtn) {
        submitBtn.onclick = function() {
          const content = prompt('请输入你的方案（文字描述）：');
          if (!content) return;
          fetch('/group/tasks/' + taskId + '/submit', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content, content_type: 'text' })
          }).then(r => r.json()).then(data => {
            if (data.error || data.detail) { alert('提交失败：' + (data.error || data.detail)); return; }
            alert('提交成功');
            window.openTaskDetail(taskId);
          }).catch(e => alert('网络错误：' + e.message));
        };
      }
      document.querySelectorAll('.pick-sub-btn').forEach(btn => {
        btn.onclick = function() {
          const sid = btn.dataset.sid;
          if (!confirm('确定选择此方案？选定后 95% 质押积分将发给该提交者。')) return;
          fetch('/group/tasks/' + taskId + '/select', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
            body: JSON.stringify({ submission_id: parseInt(sid) })
          }).then(r => r.json()).then(data => {
            if (data.error || data.detail) { alert('选择失败：' + (data.error || data.detail)); return; }
            alert('已选择，提交者获得 ' + data.winner_gets + ' 积分，群池 +' + data.pool_gets);
            window.openTaskDetail(taskId);
          }).catch(e => alert('网络错误：' + e.message));
        };
      });
    }, 100);
  }).catch(e => alert('网络错误：' + e.message));
};
