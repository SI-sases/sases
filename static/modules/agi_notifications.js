// static/modules/agi_notifications.js
// Poll main-AGI failure/notification events and surface them in the chat.
const token = () => localStorage.getItem('sases_token') || '';
let lastId = 0;
let timer = null;

async function poll() {
  if (!token() || document.hidden) return;
  const cid = window.chatState && window.chatState.conversationId;
  const q = new URLSearchParams({ after: String(lastId) });
  if (cid) q.set('conversation_id', String(cid));
  try {
    const r = await fetch('/agi/notifications?' + q.toString(), {
      headers: { 'Authorization': 'Bearer ' + token() }
    });
    if (!r.ok) return;
    const data = await r.json();
    const rows = data.notifications || [];
    if (!rows.length) return;
    lastId = Math.max(lastId, ...rows.map((x) => Number(x.id) || 0));
    rows.forEach((row) => {
      window.dispatchEvent(new CustomEvent('sases_agi_notification', { detail: row }));
    });
    await fetch('/agi/notifications/read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token() },
      body: JSON.stringify({ ids: rows.map((x) => x.id) })
    }).catch(() => {});
  } catch (e) {}
}

export function initAgiNotifications() {
  if (timer) return;
  timer = setInterval(poll, 8000);
  poll();
}

if (typeof window !== 'undefined') window.initAgiNotifications = initAgiNotifications;
