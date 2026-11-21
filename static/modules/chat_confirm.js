// static/modules/chat_confirm.js
// 定时任务确认卡：创建后出现在聊天里，可一键撤销
(function () {
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function show(d) {
    var box = document.getElementById('chat-messages');
    if (!box || !d || !d.task_id) return;
    var card = document.createElement('div');
    card.className = 'sched-card';
    card.style.cssText = 'margin:10px 14px;background:#fff;border:1px solid #cfe3ff;border-radius:10px;' +
      'padding:10px 12px;font-family:system-ui;font-size:12px;color:#333;box-shadow:0 2px 8px rgba(0,0,0,.04)';
    card.innerHTML =
      '<div style="font-weight:600;color:#1a5fb4;margin-bottom:4px">⏰ 定时任务已创建</div>' +
      '<div style="margin-bottom:4px">' + esc(d.text || d.name) + '</div>' +
      '<div style="color:#888;font-size:11px">' + esc(d.cron || '') +
      (d.next_run_at ? ' · 下次 ' + esc(String(d.next_run_at).slice(0, 16)) : '') + '</div>' +
      '<button style="margin-top:8px;border:1px solid #ddd;background:#fff;border-radius:6px;' +
      'padding:4px 10px;font-size:11px;cursor:pointer">撤销</button>';
    var btn = card.querySelector('button');
    btn.onclick = function () {
      btn.disabled = true;
      fetch('/scheduled/' + encodeURIComponent(d.task_id), {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + (localStorage.getItem('sases_token') || '') }
      }).then(function (r) { return r.json(); }).then(function () {
        btn.textContent = '已撤销';
        card.style.opacity = '0.6';
      }).catch(function () {
        btn.disabled = false;
        btn.textContent = '撤销失败';
      });
    };
    box.appendChild(card);
    box.scrollTop = box.scrollHeight;
  }

  window.addEventListener('sases_schedule_created', function (e) { show(e.detail || {}); });
})();
