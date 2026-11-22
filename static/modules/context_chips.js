// static/modules/context_chips.js
// B1: 输入区上下文 chips（引用/附件/智能体/模型/权限）
(function () {
  var lastSig = '';

  function css() {
    if (document.getElementById('context-chips-style')) return;
    var s = document.createElement('style');
    s.id = 'context-chips-style';
    s.textContent = [
      '#context-chips{display:flex;gap:6px;flex-wrap:wrap;padding:2px 12px 6px;background:var(--bg-card);}',
      '#context-chips:empty{display:none}',
      '#context-chips .ctx-chip{display:inline-flex;align-items:center;gap:4px;max-width:260px;',
      'padding:2px 8px;border-radius:10px;background:#eef4ff;color:#1a5fb4;font-size:11px;',
      'white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '#context-chips .ctx-chip.perm{background:#eef7ee;color:#2e7d32}',
      '#context-chips .ctx-chip .x{cursor:pointer;color:#888;font-weight:600}',
      '#context-chips .ctx-chip.clickable{cursor:pointer}'
    ].join('');
    document.head.appendChild(s);
  }

  function modelOf(agentId) {
    try {
      var m = window.__sasesModelsCache && window.__sasesModelsCache[agentId];
      if (m) return m.provider + (m.model_name ? ' · ' + m.model_name : '');
    } catch (e) {}
    return '';
  }

  function render() {
    var box = document.getElementById('context-chips');
    if (!box) return;
    var st = window.chatState || {};
    css();
    var _qb = document.getElementById('quote-bar');
    if (_qb && st.pendingQuote) _qb.style.display = 'none';
    var items = [];
    if (st.pendingQuote) {
      items.push({ id: 'quote', text: '引用：' + String(st.pendingQuote).replace(/\s+/g, ' ').slice(0, 24), kind: 'quote' });
    }
    var atts = Array.isArray(st.pendingAttachments) ? st.pendingAttachments : [];
    atts.forEach(function (a, i) {
      items.push({ id: 'att' + i, text: '附件：' + (a.name || '文件'), kind: 'att', index: i });
    });
    var aid = st.senderAgentId || st.agentId;
    // 智能体信息统一放在输入区切换按钮/标题，输入区不再重复渲染 🤖 provider
    var perms = {};
    try { perms = JSON.parse(localStorage.getItem('sases_perms_v1') || '{}'); } catch (e) {}
    var plist = [];
    if (perms.write) plist.push('改文件');
    if (perms.web) plist.push('联网');
    if (plist.length) items.push({ id: 'perm', text: plist.join(' · '), kind: 'perm' });

    var sig = JSON.stringify(items.map(function (x) { return x.id + x.text; }));
    if (sig === lastSig) return;
    lastSig = sig;

    box.innerHTML = '';
    items.forEach(function (it) {
      var el = document.createElement('span');
      el.className = 'ctx-chip' + (it.kind === 'perm' ? ' perm clickable' : '');
      el.textContent = it.text;
      if (it.kind === 'quote' || it.kind === 'att') {
        var x = document.createElement('span');
        x.className = 'x';
        x.textContent = '×';
        x.onclick = function (e) {
          e.stopPropagation();
          if (it.kind === 'quote') {
            st.pendingQuote = null;
            var qb = document.getElementById('quote-bar');
            if (qb) qb.style.display = 'none';
          } else if (atts.length > it.index) {
            atts.splice(it.index, 1);
          }
          lastSig = '';
          render();
        };
        el.appendChild(x);
      }
      if (it.kind === 'perm') {
        el.style.cursor = 'pointer';
        el.onclick = function () {
          var p = document.getElementById('api-pill');
          if (p) p.click();
        };
      }
      box.appendChild(el);
    });
  }

  function boot() {
    css();
    if (!document.getElementById('context-chips')) {
      var bar = document.getElementById('param-bar');
      if (bar && bar.parentNode) {
        var d = document.createElement('div');
        d.id = 'context-chips';
        bar.parentNode.insertBefore(d, bar.nextSibling);
      }
    }
    render();
    setInterval(render, 1200);
    window.addEventListener('sases_context_changed', function () { lastSig = ''; render(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
