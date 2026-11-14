// static/modules/chat_identity.js

// ========== 头像颜色哈希 ==========
function hashColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}

// ========== 更新身份按钮 ==========
export function updateIdentityButton(chatState) {
  const btn = document.getElementById('identity-btn');
  if (!btn) return;
  if (chatState.senderAgentId) {
    btn.textContent = chatState.senderAgentId.charAt(0).toUpperCase();
    btn.style.background = hashColor(chatState.senderAgentId);
    btn.style.color = '#fff';
    btn.style.borderRadius = '50%';
    btn.style.width = '28px';
    btn.style.height = '28px';
    btn.style.display = 'flex';
    btn.style.alignItems = 'center';
    btn.style.justifyContent = 'center';
  } else {
    btn.textContent = '🤖';
    btn.style.background = 'none';
    btn.style.color = '';
    btn.style.borderRadius = '';
    btn.style.width = '';
    btn.style.height = '';
    btn.style.display = '';
    btn.style.alignItems = '';
    btn.style.justifyContent = '';
  }
}

// ========== 打开身份切换页面 ==========
export async function openIdentitySwitch(chatState, api) {
  const contentHtml = `
    <div class="me-menu" id="identity-switch-list">
      <div class="me-menu-item identity-option" data-agent-id="">👤 以本人身份</div>
      <div class="subpage-placeholder">加载智能体...</div>
    </div>
  `;
  window.openSubpage('切换身份', contentHtml);

  try {
    const data = await api.listMyAgents();
    const agents = (data.agents || []).filter(a => !(a.agent_id || '').startsWith('sases_assistant'));
    const container = document.getElementById('identity-switch-list');
    if (agents.length === 0) {
      container.innerHTML = '<div class="subpage-placeholder">暂无智能体</div>';
      return;
    }
    let html = '<div class="me-menu-item identity-option" data-agent-id="">👤 以本人身份</div>';
    agents.forEach(agent => {
      html += `
        <div class="me-menu-item identity-option" data-agent-id="${agent.agent_id}">
          <span class="menu-icon">🤖</span>
          ${agent.name}
        </div>
      `;
    });
    container.innerHTML = html;

    container.querySelectorAll('.identity-option').forEach(opt => {
      opt.addEventListener('click', () => {
        chatState.senderAgentId = opt.dataset.agentId || null;
        localStorage.setItem('sases_sender_agent_id', chatState.senderAgentId || '');
        window.closeSubpage();
        const baseTitle = document.getElementById('chat-window-title').textContent.split(' (')[0];
        document.getElementById('chat-window-title').textContent = chatState.senderAgentId ? baseTitle + ' (智能体)' : baseTitle;
        updateIdentityButton(chatState);
      });
    });
  } catch (e) {
    document.getElementById('identity-switch-list').innerHTML = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }
}