// static/modules/chat_a2a.js
// A2A 执行中浮动提示
(function () {
  var timer = null;

  function hide() {
    var el = document.getElementById('a2a-progress');
    if (el) el.remove();
    if (timer) { clearTimeout(timer); timer = null; }
  }

  function show(d) {
    var el = document.getElementById('a2a-progress');
    if (!el) {
      el = document.createElement('div');
      el.id = 'a2a-progress';
      el.style.cssText = 'position:fixed;left:50%;top:72px;transform:translateX(-50%);z-index:60;' +
        'background:rgba(0,122,255,.94);color:#fff;font-size:12px;padding:6px 14px;border-radius:16px;' +
        'box-shadow:0 4px 14px rgba(0,122,255,.3);font-family:system-ui';
      document.body.appendChild(el);
    }
    el.textContent = '🤖 ' + ((d && d.content) || '对方智能体正在执行…');
    if (timer) clearTimeout(timer);
    timer = setTimeout(hide, 30000);
  }

  window.addEventListener('sases_a2a_progress', function (e) { show(e.detail || {}); });
  window.addEventListener('sases_new_message', function () { hide(); });
})();
