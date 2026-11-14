// static/modules/ws_client.js
// 用户级 WebSocket：接收单聊消息推送

let _ws = null;
let _reconnectTimer = null;

export function connectUserWs() {
  if (_ws && _ws.readyState <= 1) return;
  fetch('/auth/me', {
    headers: { 'Authorization': 'Bearer ' + (localStorage.getItem('sases_token') || '') }
  }).then(r => r.json()).then(me => {
    const uid = me.user_id;
    if (!uid) return;
    _openWs(uid);
  }).catch(() => {});
}

function _openWs(uid) {
  try {
    const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    const url = proto + location.host + '/ws/user/' + uid;
    _ws = new WebSocket(url);
    
    // 【关键修复】：暴露给全局，方便在 Console 调试
    window._ws = _ws; 

    _ws.onopen = () => {
      console.log('[user-ws] connected for user', uid);
      if (_ws._hb) clearInterval(_ws._hb);
      _ws._hb = setInterval(() => {
        if (_ws && _ws.readyState === 1) _ws.send('ping');
      }, 25000);
    };
    _ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        // 兼容不同的推送类型名称
        if (d && (d.type === 'new_message' || d.type === 'sases_new_message')) {
          window.dispatchEvent(new CustomEvent('sases_new_message', { detail: d }));
        }
      } catch (err) {}
    };
    _ws.onclose = () => {
      console.log('[user-ws] closed, will reconnect in 3s');
      if (_ws && _ws._hb) clearInterval(_ws._hb);
      _ws = null;
      if (_reconnectTimer) clearTimeout(_reconnectTimer);
      _reconnectTimer = setTimeout(() => _openWs(uid), 3000);
    };
    _ws.onerror = () => {};
  } catch (e) {
    console.warn('[user-ws] open failed:', e);
  }
}