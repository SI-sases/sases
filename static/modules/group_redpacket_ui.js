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


{"success": true, "answer": "window.openGroupRedPacket = async function(packetId) {\n  try {\n    const detail = await fetch('/group/red-packets/' + packetId, {\n      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }\n    }).then(r => r.json());\n    if (detail.error || detail.detail) { alert('加载失败：' + (detail.error || detail.detail)); return; }\n    let claimsHtml = '';\n    if (detail.claims && detail.claims.length > 0) {\n      claimsHtml = '<div style=\"margin-top:20px;\"><div style=\"font-size:13px;color:#999;margin-bottom:8px;\">领取记录</div>';\n      detail.claims.forEach(c => {\n        claimsHtml += '<div style=\"display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f5f5f5;font-size:13px;\"><span>' + (c.username || '匿名') + '</span><span style=\"color:#f59e0b;font-weight:600;\">' + c.amount + ' 积分</span></div>';\n      });\n      claimsHtml += '</div>';\n    }\n    let bodyHtml = '';\n    if (detail.claimed_by_me !== null && detail.claimed_by_me !== undefined) {\n      bodyHtml = '<div style=\"font-size:48px;font-weight:700;color:#f59e0b;margin:20px 0;\">' + detail.claimed_by_me + '</div><div style=\"font-size:14px;color:#666;\">已存入你的积分</div>';\n    } else if (detail.status === 'empty') {\n      bodyHtml = '<div style=\"font-size:36px;color:#999;margin:20px 0;\">已抢完</div>';\n    } else if (detail.status === 'expired') {\n      bodyHtml = '<div style=\"font-size:36px;color:#999;margin:20px 0;\">已过期</div>';\n    } else {\n      bodyHtml = '<button id=\"grp-rp-claim-btn\" style=\"width:180px;height:180px;border-radius:50%;background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#fff;font-size:24px;font-weight:700;border:none;cursor:pointer;margin:20px auto;display:block;box-shadow:0 8px 24px rgba(245,158,11,0.3);\">開</button>';\n    }\n    const html = '<div style=\"text-align:center;padding:30px 20px;\">'\n      + '<div style=\"font-size:18px;font-weight:600;margin-bottom:8px;\">' + (detail.message || '恭喜发财') + '</div>'\n      + '<div style=\"font-size:13px;color:#999;margin-bottom:20px;\">来自 ' + (detail.sender_name || '群友') + ' 的群红包</div>'\n      + '<div style=\"background:linear-gradient(135deg,#fef3c7,#fed7aa);border-radius:16px;padding:30px 20px;margin:0 auto;\">'\n      + bodyHtml\n      + '<div style=\"font-size:12px;color:#92400e;margin-top:12px;\">' + detail.claimed_count + '/' + detail.total_count + ' 已领取 · 总额 ' + detail.total_amount + ' 积分</div>'\n      + '</div>'\n      + claimsHtml\n      + '</div>';\n    window.openSubpage('群红包', html);\n    setTimeout(() => {\n      const btn = document.getElementById('grp-rp-claim-btn');\n      if (btn) {\n        btn.onclick = async function() {\n          btn.disabled = true;\n          btn.textContent = '...';\n          try {\n            const resp = await fetch('/group/red-packets/' + packetId + '/claim', {\n              method: 'POST',\n              headers: { 'Authorization': 'Bearer ' + localStorage.getItem('sases_token') }\n            });\n            const data = await resp.json();\n            if (data.error || data.detail) { alert('领取失败：' + (data.error || data.detail)); btn.disabled = false; btn.textContent = '開'; return; }\n            if (window.showGroupToast) window.showGroupToast('🧧 你抢到了 ' + data.amount + ' 积分');\n            window.openGroupRedPacket(packetId);\n            if (typeof loadGroupMessages === 'function') loadGroupMessages();\n          } catch (e) { alert('网络错误：' + e.message); btn.disabled = false; btn.textContent = '開'; }\n        };\n      }\n    }, 100);\n  } catch (e) { alert('网络错误：' + e.message); }\n};\n", "length": 3502}

window.openGroupRedPacket = openGroupRedPacket;

