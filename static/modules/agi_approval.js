// static/modules/agi_approval.js
// Render pending AGI approvals inside the main-AGI chat window.
const token = () => localStorage.getItem('sases_token') || '';

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

export async function loadAgiApprovals() {
  const msgs = document.getElementById('chat-messages');
  if (!msgs || !window.chatState || window.chatState.agentId !== '__main_agi__') return;
  try {
    const r = await fetch('/agi/approvals', { headers: { 'Authorization': 'Bearer ' + token() } });
    if (!r.ok) return;
    const data = await r.json();
    (data.approvals || []).forEach((item) => {
      if (document.querySelector(`[data-agi-approval="${item.id}"]`)) return;
      const card = document.createElement('div');
      card.className = 'message assistant';
      card.dataset.agiApproval = String(item.id);
      card.innerHTML = '<div style="font-weight:650;margin-bottom:6px;">⚠️ 需要审批</div>' +
        '<div style="font-size:13px;color:#555;margin-bottom:8px;">' +
        esc(item.description || item.tool) + '<br>风险：' + esc(item.risk || 'high') + '</div>' +
        '<button data-a="allow" style="margin-right:6px;">允许</button>' +
        '<button data-a="deny">拒绝</button>';
      msgs.appendChild(card);
      msgs.scrollTop = msgs.scrollHeight;
      card.querySelector('[data-a="allow"]').onclick = () => decide(item.id, 'allow', card);
      card.querySelector('[data-a="deny"]').onclick = () => decide(item.id, 'deny', card);
    });
  } catch (e) {}
}

async function decide(id, decision, card) {
  try {
    const r = await fetch('/agi/approvals/decide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token() },
      body: JSON.stringify({ id, decision })
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    card.innerHTML = '<div style="font-weight:600;">' +
      (decision === 'allow' ? '✅ 已允许' : '⛔ 已拒绝') + '</div>';
    setTimeout(() => card.remove(), 2500);
  } catch (e) {
    card.querySelector('button')?.setAttribute('disabled', 'disabled');
    card.insertAdjacentHTML('beforeend', '<div style="color:#d93025;font-size:12px;">提交失败</div>');
  }
}

if (typeof window !== 'undefined') window.loadAgiApprovals = loadAgiApprovals;
