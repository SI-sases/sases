window.openSwarmConfig = async function(groupId) {
  let swarmEnabled = false;
  let sharedAgents = [];
  let allAgents = [];

  try {
    const resp = await fetch('/group/' + groupId + '/swarm/status', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    swarmEnabled = !!data.swarm_enabled;
  } catch (e) {}

  try {
    const resp = await fetch('/group/' + groupId + '/resource-pool', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    sharedAgents = data.pool || [];
  } catch (e) {}

  try {
    const resp = await fetch('/agents/list', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    allAgents = data.agents || [];
  } catch (e) {}

  const sharedIds = new Set(sharedAgents.map(a => a.agent_id));

  const renderPage = () => {
    let agentsHtml = '';
    if (allAgents.length === 0) {
      agentsHtml = '<div style="text-align:center;color:#999;padding:20px 0;font-size:13px;">你还没有智能体，请先在"我的-模型管理"添加</div>';
    } else {
      allAgents.forEach(a => {
        const checked = sharedIds.has(a.agent_id);
        agentsHtml += '<div class="me-menu-item swarm-agent-row" data-agentid="' + a.agent_id + '" style="cursor:pointer;">';
        agentsHtml += '<div style="flex:1;min-width:0;">';
        agentsHtml += '<div style="font-size:14px;color:#333;">' + (a.name || a.agent_id) + '</div>';
        agentsHtml += '<div style="font-size:12px;color:#999;margin-top:2px;">' + (a.detail || a.type || '') + '</div>';
        agentsHtml += '</div>';
        agentsHtml += '<div class="switch' + (checked ? ' on' : '') + '" style="pointer-events:none;"><div class="slider"></div></div>';
        agentsHtml += '</div>';
      });
    }

    const html = `
      <div class="me-menu">
        <div class="me-menu-item" id="swarm-toggle-row" style="cursor:pointer;">
          <span class="menu-label">蜂群模式</span>
          <div class="switch${swarmEnabled ? ' on' : ''}" id="swarm-toggle-switch"><div class="slider"></div></div>
        </div>
      </div>
      <div class="section-title">共享给群成员的智能体</div>
      <div class="me-menu" id="swarm-agents-list">
        ${agentsHtml}
      </div>
      <div class="me-menu">
        <div class="me-menu-item" id="swarm-usage-entry" style="cursor:pointer;">
          <span class="menu-label">使用统计</span>
          <span class="menu-arrow">›</span>
        </div>
      </div>
      <div style="padding:12px;font-size:12px;color:#999;line-height:1.6;">
        开启后，群成员切换身份时可以选择你共享的智能体，使用其模型资源。每人每日 100 次配额。
      </div>
    `;
    window.openSubpage('蜂群模式管理', html, {
      showMore: false,
      returnAction: () => window.openGroupSettings()
    });

    setTimeout(() => {
      const toggle = document.getElementById('swarm-toggle-row');
      if (toggle) {
        toggle.onclick = async () => {
          const newVal = !swarmEnabled;
          try {
            const resp = await fetch('/group/' + groupId + '/swarm/toggle', {
              method: 'POST',
              headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
              body: JSON.stringify({ enabled: newVal })
            });
            const data = await resp.json();
            if (data.error || data.detail) { alert('切换失败：' + (data.error || data.detail)); return; }
            swarmEnabled = newVal;
            const sw = document.getElementById('swarm-toggle-switch');
            if (sw) {
              if (newVal) sw.classList.add('on'); else sw.classList.remove('on');
            }
          } catch (e) { alert('网络错误：' + e.message); }
        };
      }

      document.querySelectorAll('.swarm-agent-row').forEach(row => {
        row.onclick = async () => {
          const agentId = row.dataset.agentid;
          const isShared = sharedIds.has(agentId);
          try {
            if (isShared) {
              const resp = await fetch('/group/' + groupId + '/resource-pool/unbind', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId })
              });
              const data = await resp.json();
              if (data.error || data.detail) { alert('取消共享失败：' + (data.error || data.detail)); return; }
              sharedIds.delete(agentId);
            } else {
              const resp = await fetch('/group/' + groupId + '/resource-pool/bind', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId, model_id: agentId, daily_limit: 100 })
              });
              const data = await resp.json();
              if (data.error || data.detail) { alert('共享失败：' + (data.error || data.detail)); return; }
              sharedIds.add(agentId);
            }
            const sw = row.querySelector('.switch');
            if (sw) {
              if (sharedIds.has(agentId)) sw.classList.add('on'); else sw.classList.remove('on');
            }
          } catch (e) { alert('网络错误：' + e.message); }
        };
      });

      const usage = document.getElementById('swarm-usage-entry');
      if (usage) usage.onclick = () => openSwarmUsage(groupId);
    }, 300);
  };

  renderPage();
};

window.openSwarmUsage = async function(groupId) {
  try {
    const resp = await fetch('/group/' + groupId + '/resource-usage?days=7', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }
    });
    const data = await resp.json();
    if (data.error || data.detail) { alert('加载失败：' + (data.error || data.detail)); return; }

    const today = data.today || {};
    const topUsers = data.top_users || [];
    const trend = data.trend || [];

    let topHtml = '';
    if (topUsers.length === 0) {
      topHtml = '<div style="text-align:center;color:#999;padding:20px 0;font-size:13px;">暂无使用记录</div>';
    } else {
      topUsers.forEach((u, idx) => {
        topHtml += '<div class="me-menu-item">';
        topHtml += '<span class="menu-label">' + (idx + 1) + '. ' + (u.username || '匿名') + '</span>';
        topHtml += '<span class="menu-value">' + (u.calls || 0) + ' 次</span>';
        topHtml += '</div>';
      });
    }

    let trendHtml = '';
    if (trend.length === 0) {
      trendHtml = '<div style="text-align:center;color:#999;padding:20px 0;font-size:13px;">暂无趋势数据</div>';
    } else {
      trend.forEach(t => {
        trendHtml += '<div class="me-menu-item">';
        trendHtml += '<span class="menu-label">' + t.day + '</span>';
        trendHtml += '<span class="menu-value">' + (t.calls || 0) + ' 次</span>';
        trendHtml += '</div>';
      });
    }

    const html = `
      <div class="wallet-card" style="background: linear-gradient(135deg, #8b5cf6, #6366f1);">
        <div class="wallet-label">今日调用</div>
        <div class="wallet-balance">${today.calls || 0}</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">Token 消耗 ${today.tokens || 0}</div>
      </div>
      <div class="section-title">今日活跃用户</div>
      <div class="me-menu">
        ${topHtml}
      </div>
      <div class="section-title">近 7 日趋势</div>
      <div class="me-menu">
        ${trendHtml}
      </div>
    `;
    window.openSubpage('使用统计', html, {
      showMore: false,
      returnAction: () => openSwarmConfig(groupId)
    });
  } catch (e) { alert('网络错误：' + e.message); }
};
