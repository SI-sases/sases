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
      'padding:4px 10px;font-size:11px;color:#666;cursor:pointer}'
    ].join('');
    document.head.appendChild(s);
  }

  function box() {
    var msgs = document.getElementById('chat-messages');
    if (!msgs) return null;
    if (!card || !card.parentNode) {
      card = document.createElement('div');
      card.id = 'run-progress-card';
      card.innerHTML = '<div class="rp-head"><span class="rp-dot"></span><span class="rp-title">执行中</span></div><div class="rp-lines"></div>';
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
      meta.textContent = '过程详情可在右侧 trace 抽屉查看';
      c.appendChild(meta);
    }
    if (runId) {
      var btn = document.createElement('button');
      btn.className = 'rp-revert';
      btn.textContent = '撤销本次修改';
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
          btn.textContent = '已撤销：恢复 ' + ((j.restored || []).length) + '，删除 ' + ((j.deleted || []).length);
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
      addLine('⏳', '步骤 ' + steps + tool, '');
    } else if (et === 'step_done' || et === 'tool_result') {
      var ok = (d.status || '') === 'success';
      var preview = (d.output_preview || d.content || '').replace(/\s+/g, ' ').slice(0, 80);
      addLine(ok ? '✓' : '✗', (ok ? '完成' : '失败') + tool + (preview ? ' · ' + preview : ''),
              ok ? 'done' : 'fail', d.output_detail || '');
    } else if (et === 'run_end') {
      finish(d.status === 'interrupted' ? '已中断' : '已完成');
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
