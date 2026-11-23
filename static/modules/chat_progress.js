// static/modules/chat_progress.js
// UX-2: 聊天内联进度卡（不替代 trace 抽屉）
(function () {
  var card = null;
  var runId = null;
  var steps = 0;
  var seen = {};

  function css() {
    if (document.getElementById('run-progress-style')) return;
    var s = document.createElement('style');
    s.id = 'run-progress-style';
    s.textContent = [
      '#run-progress-card{margin:10px 14px;background:#f7f9fc;border:1px solid #e3e9f2;',
      'border-radius:10px;padding:8px 10px;font-size:12px;color:#333;font-family:system-ui}',
      '#run-progress-card .rp-head{display:flex;align-items:center;gap:6px;font-weight:600;margin-bottom:4px}',
      '#run-progress-card .rp-dot{width:8px;height:8px;border-radius:50%;background:#007aff;animation:rp-pulse 1.2s infinite}',
      '@keyframes rp-pulse{0%{opacity:.3}50%{opacity:1}100%{opacity:.3}}',
      '#run-progress-card .rp-line{display:flex;gap:6px;padding:2px 0;color:#555}',
      '#run-progress-card .rp-line .rp-ico{width:14px}',
      '#run-progress-card .rp-line.done .rp-ico{color:#1a9c4a}',
      '#run-progress-card .rp-line.fail .rp-ico{color:#d93025}',
      '#run-progress-card .rp-meta{color:#999;font-size:10px;margin-top:2px}',
      '#run-progress-card .rp-detail{white-space:pre-wrap;background:#fff;border:1px solid #eee;',
      'border-radius:6px;padding:6px;margin:4px 0 2px 20px;font-size:11px;color:#555;max-height:200px;overflow:auto}',
      '#run-progress-card .rp-line.clickable{cursor:pointer}',
      '#run-progress-card .rp-revert{margin-top:6px;border:1px solid #ddd;background:#fff;border-radius:6px;',
      'padding:4px 10px;font-size:11px;color:#666;cursor:pointer}',
      '#run-error-card{margin:10px 14px;background:#fff5f5;border:1px solid #ffb3b3;border-radius:10px;',
      'padding:10px 12px;font-size:12px;color:#333;font-family:system-ui}',
      '#run-error-card .er-title{font-weight:600;color:#d93025;margin-bottom:4px}',
      '#run-error-card .er-desc{color:#666;margin-bottom:8px;word-break:break-all}',
      '#run-error-card button{border:1px solid #ddd;background:#fff;border-radius:6px;padding:4px 10px;',
      'margin-right:6px;font-size:11px;cursor:pointer}'
    ].join('');
    document.head.appendChild(s);
  }

  function box() {
    var msgs = document.getElementById('chat-messages');
    if (!msgs) return null;
    if (!card || !card.parentNode) {
      card = document.createElement('div');
      card.id = 'run-progress-card';
      card.innerHTML = '<div class="rp-head"><span class="rp-dot"></span><span class="rp-title">' + t('cpr_running') + '</span></div><div class="rp-lines"></div>';
      msgs.appendChild(card);
    }
    return card;
  }

  function addLine(icon, text, cls, detail) {
    var c = box();
    if (!c) return;
    var lines = c.querySelector('.rp-lines');
    var row = document.createElement('div');
    row.className = 'rp-line ' + (cls || '') + (detail ? ' clickable' : '');
    row.innerHTML = '<span class="rp-ico">' + icon + '</span><span>' + text + '</span>';
    if (detail) {
      var det = document.createElement('div');
      det.className = 'rp-detail';
      det.style.display = 'none';
      det.textContent = detail;
      row.appendChild(det);
      row.onclick = function (e) {
        e.stopPropagation();
        det.style.display = det.style.display === 'none' ? 'block' : 'none';
      };
    }
    lines.appendChild(row);
    var msgs = document.getElementById('chat-messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function lastUserText() {
    var rows = document.querySelectorAll('#chat-messages [data-role="user"]');
    if (!rows.length) return '';
    var el = rows[rows.length - 1];
    var b = el.children[0];
    return b ? (b.textContent || '').trim() : '';
  }

  function revertRun(runId, btn) {
    if (!confirm(t('cpr_restore_confirm'))) return;
    btn.disabled = true;
    fetch('/supervisor/runs/' + runId + '/revert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (localStorage.getItem('sases_token') || '') },
      body: JSON.stringify({ confirm: true })
    }).then(function (r) { return r.json(); }).then(function (j) {
      btn.textContent = t('cpr_undone') + ' ' + ((j.restored || []).length) + '，' + t('cpr_undone_deleted') + ' ' + ((j.deleted || []).length);
    }).catch(function () { btn.disabled = false; btn.textContent = t('cpr_undo_failed'); });
  }

  function showError(runId, tool, preview) {
    if (document.getElementById('run-error-card')) return;
    var msgs = document.getElementById('chat-messages');
    if (!msgs) return;
    var d = document.createElement('div');
    d.id = 'run-error-card';
    d.innerHTML = '<div class="er-title">⚠️ ' + t('cpr_failed_title') + '</div>' +
      '<div class="er-desc">' + (tool ? t('cpr_tool') + '：' + tool + ' · ' : '') + (preview || t('cpr_no_step')) + '</div>' +
      '<button data-e="retry">' + t('cpr_retry') + '</button>' +
      '<button data-e="undo">' + t('cpr_undo_this') + '</button>' +
      '<button data-e="detail">' + t('cpr_detail') + '</button>';
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    d.querySelector('[data-e="retry"]').onclick = function () {
      var txt = lastUserText();
      if (!txt) return;
      var input = document.getElementById('chat-input');
      if (!input) return;
      input.value = txt;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      var btn = document.getElementById('send-btn');
      if (btn) btn.click();
    };
    d.querySelector('[data-e="undo"]').onclick = function (e) {
      revertRun(runId, e.target);
    };
    d.querySelector('[data-e="detail"]').onclick = function () {
      var chip = document.getElementById('trace-chip');
      if (chip && chip.style.display !== 'none') chip.click();
    };
  }

  function finish(text) {
    var c = box();
    if (!c) return;
    c.querySelector('.rp-title').textContent = text;
    var d = c.querySelector('.rp-dot');
    if (d) d.style.animation = 'none';
    var meta = c.querySelector('.rp-meta');
    if (!meta) {
      meta = document.createElement('div');
      meta.className = 'rp-meta';
      meta.textContent = t('cpr_trace_hint');
      c.appendChild(meta);
    }
    if (runId) {
      var btn = document.createElement('button');
      btn.className = 'rp-revert';
      btn.textContent = t('cpr_undo_this');
      btn.onclick = function () {
        if (!confirm('恢复本次运行修改/创建的文件？')) return;
        btn.disabled = true;
        fetch('/supervisor/runs/' + runId + '/revert', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (localStorage.getItem('sases_token') || '')
          },
          body: JSON.stringify({ confirm: true })
        }).then(function (r) { return r.json(); }).then(function (j) {
          btn.textContent = t('cpr_undone') + ' ' + ((j.restored || []).length) + '，' + t('cpr_undone_deleted') + ' ' + ((j.deleted || []).length);
        }).catch(function (e) {
          btn.disabled = false;
          btn.textContent = '撤销失败';
        });
      };
      c.appendChild(btn);
    }
  }

  window.addEventListener('sases_task_trace', function (e) {
    var d = e.detail || {};
    var cid = window.chatState && window.chatState.conversationId;
    if (!cid || String(d.conversation_id) !== String(cid)) return;
    if (d.seq && seen[d.seq]) return;
    if (d.seq) seen[d.seq] = 1;
    if (d.run_id && d.run_id !== runId) {
      runId = d.run_id;
      steps = 0;
      card = null;
      seen = {};
      if (d.seq) seen[d.seq] = 1;
    }
    css();
    var et = d.event_type || '';
    var tool = d.tool ? ' · ' + d.tool : '';
    if (et === 'step_start') {
      steps += 1;
      addLine('⏳', t('cpr_step') + ' ' + steps + tool, '');
    } else if (et === 'step_done' || et === 'tool_result') {
      var ok = (d.status || '') === 'success';
      var preview = (d.output_preview || d.content || '').replace(/\s+/g, ' ').slice(0, 80);
      addLine(ok ? '✓' : '✗', (ok ? t('cpr_done') : t('cpr_failed')) + tool + (preview ? ' · ' + preview : ''),
              ok ? 'done' : 'fail', d.output_detail || '');
      if (!ok) showError(d.run_id, d.tool, preview);
    } else if (et === 'run_end') {
      finish(d.status === 'interrupted' ? t('cpr_interrupted') : (d.status === 'failed' ? t('cpr_failed') : t('cpr_completed')));
    } else if (et === 'async_done') {
      addLine('⏱', '异步任务完成', 'done');
    }
  });

  // 会话切换时移除旧卡
  setInterval(function () {
    var cid = window.chatState && window.chatState.conversationId;
    if (card && card.dataset.cid && String(card.dataset.cid) !== String(cid)) {
      card.remove();
      card = null;
    }
  }, 1500);
})();
