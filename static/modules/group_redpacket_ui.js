import { api } from './api.js';
window.openGroupRedPacketDialog = function(groupId) {
  const html = `
    <div style="padding:16px;">
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包类型</div>
        <select id="grp-rp-type" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;background:#fff;">
          <option value="lucky">拼手气红包（金额随机）</option>
          <option value="normal">普通红包（金额均分）</option>
        </select>
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包总金额（积分）</div>
        <input id="grp-rp-total" type="number" value="10" min="1" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">红包个数</div>
        <input id="grp-rp-count" type="number" value="5" min="1" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="margin-bottom:16px;">
        <div style="font-size:13px;color:#666;margin-bottom:6px;">留言（可选）</div>
        <input id="grp-rp-msg" type="text" placeholder="恭喜发财，大吉大利" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;">
      </div>
      <div style="background:#fff7e6;border:1px solid #ffd591;border-radius:6px;padding:10px;margin-bottom:20px;font-size:12px;color:#874d00;line-height:1.6;">
        ⚠️ 红包 24 小时内有效，未领完的金额将退回你的积分账户。
      </div>
      <button id="grp-rp-submit" style="width:100%;padding:12px;background:#ef4444;color:#fff;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;">塞钱进红包</button>
    </div>
  `;
  window.openSubpage('发群红包', html);
  setTimeout(function() {
    const btn = document.getElementById('grp-rp-submit');
    if (!btn) return;
    btn.onclick = function() {
      const type = document.getElementById('grp-rp-type').value;
      const total = parseFloat(document.getElementById('grp-rp-total').value);
      const count = parseInt(document.getElementById('grp-rp-count').value);
      const msg = document.getElementById('grp-rp-msg').value || '';
      if (!total || total < 1) { alert('总金额最少 1'); return; }
      if (!count || count < 1) { alert('个数最少 1'); return; }
      fetch('/group/' + groupId + '/red-packets/create', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token'), 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_amount: total, total_count: count, message: msg, source_type: 'user', packet_type: type })
      }).then(r => r.json()).then(data => {
        if (data.error || data.detail) { alert('发布失败：' + (data.error || data.detail)); return; }
        alert('红包已发送');
        if (typeof window.closeSubpage === 'function') window.closeSubpage();
        // 乐观渲染（不重拉全量）
        try {
          const cardPayload = JSON.stringify({
            packet_id: data.packet_id,
            total_amount: total,
            total_count: count,
            message: msg,
            source_type: 'user',
            packet_type: type
          });
          if (typeof appendGroupMessage === 'function') {
            appendGroupMessage('我', '[RED_PACKET]:' + cardPayload, true);
          }
        } catch (e) {}
        if (typeof loadGroupRedPackets === 'function') loadGroupRedPackets();
      }).catch(e => alert('网络错误：' + e.message));
    };
  }, 300);
};


async function loadGroupRedPackets() {
  if (!currentGroupId) return;
  try {
    const data = await api.getActiveGroupRedPackets(currentGroupId);
    const packets = (data && data.packets) || [];
    const bar = document.getElementById('group-red-packet-bar');
    const text = document.getElementById('group-red-packet-bar-text');
    if (!bar || !text) return;
    if (packets.length === 0) {
      bar.style.display = 'none';
      return;
    }
    text.textContent = '🧧 待抢红包 (' + packets.length + ')';
    bar.style.display = 'flex';
    bar.onclick = function() {
      openRedPacketListPage(packets);
    };
  } catch (e) {
    console.log('loadGroupRedPackets error:', e);
  }
}

function openRedPacketListPage(packets) {
  let html = '<div style="padding:12px;">';
  packets.forEach(p => {
    const isPool = p.source_type === 'group_pool';
    const title = isPool ? '🎁 群福利红包' : '🧧 群红包';
    html += '<div class="rp-list-item" data-pid="' + p.id + '" style="border:1px solid #eee;border-radius:8px;padding:12px;margin-bottom:10px;cursor:pointer;background:' + (isPool ? '#f5f3ff' : '#fff7ed') + ';">';
    html += '<div style="font-size:15px;font-weight:600;margin-bottom:4px;">' + title + '</div>';
    html += '<div style="font-size:12px;color:#666;">' + (p.total_amount || 0) + ' 积分 · 已抢 ' + (p.claimed_count || 0) + '/' + (p.total_count || 0) + '</div>';
    if (p.message) {
      html += '<div style="font-size:12px;color:#999;margin-top:4px;">' + p.message + '</div>';
    }
    html += '</div>';
  });
  html += '</div>';
  window.openSubpage('待抢红包', html);
  setTimeout(function() {
    document.querySelectorAll('.rp-list-item').forEach(el => {
      el.onclick = function() {
        if (typeof window.openGroupRedPacket === 'function') window.openGroupRedPacket(parseInt(el.dataset.pid));
      };
    });
  }, 100);
}

window.loadGroupRedPackets = loadGroupRedPackets;
