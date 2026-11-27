// static/modules/frontend_errors.js
// Report a small, PII-free frontend event to the main AGI proxy.
const recent = new Map();

function token() {
  try { return localStorage.getItem('sases_token') || ''; } catch (e) { return ''; }
}

export function reportSasesEvent(event, error = '', extra = {}) {
  const key = event + '|' + String(error).slice(0, 120);
  const now = Date.now();
  if (recent.has(key) && now - recent.get(key) < 30000) return;
  recent.set(key, now);
  try {
    fetch('/agi/frontend-event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token()
      },
      body: JSON.stringify({
        event,
        error: String(error || '').slice(0, 500),
        page: location.pathname,
        url: location.href,
        extra
      })
    }).catch(() => {});
  } catch (e) {}
}

if (typeof window !== 'undefined' && !window.__sasesFrontendErrors) {
  window.__sasesFrontendErrors = true;
  window.reportSasesEvent = reportSasesEvent;
  window.addEventListener('error', (e) => {
    reportSasesEvent('frontend_error', e.message || 'error', { line: e.lineno, file: e.filename });
  });
  window.addEventListener('unhandledrejection', (e) => {
    reportSasesEvent('unhandled_rejection', String(e.reason || ''));
  });
}
