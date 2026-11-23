// P2-1: 写/网络/命令审批卡
import { t } from './i18n.js';
// P2-1: 写/网络/命令审批卡
(function () {
  function css() {
    if (document.getElementById('approval-style')) return;
    var s = document.createElement('style');
    s.id = 'approval-style';
    s.textContent = [
      '#approval-card{margin:10px 14px;background:#fffaf0;border:1px solid #ffd591;border-radius:10px;',
      'padding:10px 12px;font-size:13px;color:#333;font-family:system-ui}',
      '#approval-card .ap-title{font-weight:600;margin-bottom:4px}',
      '#approval-card .ap-desc{color:#666;font-size:12px;margin-bottom:8px;word-break:break-all}',
      '#approval-card button{border:1px solid #ddd;background:#fff;border-radius:6px;padding:5px 10px;',
      'margin-right:6px;cursor:pointer;font-size:12px}',
      '#approval-card button.primary{background:#007aff;border-color:#007aff;color:#fff}',
      '#approval-card button.danger{color:#d93025}'
    ].join('');
    document.head.appendChild(s);
  }

  function token() { return localStorage.getItem('sases_token') || ''; }

  function send(runId, stepId, decision, scope, card) {
    fetch('/supervisor/runs/' + runId + '/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token() },
      body: JSON.stringify({ step_id: String(stepId), decision: decision, scope: scope })
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      card.innerHTML = '<div class="ap-title">' + (decision === 'allow' ? '✅ ' + t('ca_allowed') : '⛔ ' + t('ca_denied')) + '</div>' +
        '<div class="ap-desc">' + t('ca_decision_desc') + '</div>';
      setTimeout(function () { card.remove(); }, 4000);
    }).catch(function (e) {
      card.querySelector('.ap-desc').textContent = t('ca_submit_failed') + '：' + e.message;
    });
  }

  window.addEventListener('sases_approval_request', function (e) {
    var d = e.detail || {};
    var cid = window.chatState && window.chatState.conversationId;
    if (cid && d.conversation_id && String(d.conversation_id) !== String(cid)) return;
    css();
    var msgs = document.getElementById('chat-messages');
    if (!msgs) return;
    var card = document.createElement('div');
    card.id = 'approval-card';
    card.innerHTML = '<div class="ap-title">⚠️ ' + t('ca_confirm_needed') + '</div>' +
      '<div class="ap-desc">' + t('ca_tool') + '：' + (d.tool || t('ca_tool')) +
      (d.description ? ' · ' + d.description : '') + '</div>' +
      '<button class="primary" data-a="once">' + t('ca_allow_once') + '</button>' +
      '<button data-a="session">总是允许</button>' +
      '<button class="danger" data-a="deny">拒绝</button>';
    msgs.appendChild(card);
    msgs.scrollTop = msgs.scrollHeight;
    card.querySelector('[data-a="once"]').onclick = function () {
      send(d.run_id, d.step_id, 'allow', 'once', card);
    };
    card.querySelector('[data-a="session"]').onclick = function () {
      send(d.run_id, d.step_id, 'allow', 'session', card);
    };
    card.querySelector('[data-a="deny"]').onclick = function () {
      send(d.run_id, d.step_id, 'deny', 'once', card);
    };
  });
})();
