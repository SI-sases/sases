// static/modules/tool_market.js
// 工具市场：外部工具安装 / 启停 / 卸载 + 内置工具清单
// 入口：window.SASES.toolMarket.open()

import { openSubpage } from './subpage.js';

import { t } from './i18n.js';
const TOKEN_KEY = 'sases_tools_admin_token';
let _root = null;

function _auth() {
  return localStorage.getItem('sases_token') || '';
}

function _adminToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

function _headers(admin) {
  const h = { Authorization: 'Bearer ' + _auth() };
  if (admin && _adminToken()) h['X-Admin-Token'] = _adminToken();
  return h;
}

async function _json(path, opts = {}) {
  const r = await fetch(path, opts);
  let data = null;
  try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw new Error((data && (data.detail || data.message)) || ('HTTP ' + r.status));
  return data;
}

function _css() {
  if (document.getElementById('tm-style')) return;
  const css = `
#tool-market-root{padding:12px;font-family:system-ui,-apple-system,sans-serif;font-size:13px;color:#222}
.tm-card{background:#fff;border:1px solid #eee;border-radius:10px;padding:12px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.03)}
.tm-card h3{margin:0 0 8px;font-size:14px}
.tm-row{display:flex;align-items:center;gap:8px;padding:8px 4px;border-bottom:1px solid #f4f4f4}
.tm-row:last-child{border-bottom:none}
.tm-main{flex:1;min-width:0}
.tm-name{font-weight:600;color:#222}
.tm-sub{color:#999;font-size:11px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tm-badge{display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;margin-left:6px;background:#eef4ff;color:#1a73e8}
.tm-badge.off{background:#f2f2f2;color:#888}
.tm-btn{border:1px solid #ddd;background:#fff;border-radius:6px;padding:4px 8px;cursor:pointer;font-size:12px}
.tm-btn.primary{background:#007aff;border-color:#007aff;color:#fff}
.tm-btn.danger{color:#d93025;border-color:#f3c3c0}
.tm-btn:disabled{opacity:.5;cursor:not-allowed}
.tm-input{width:100%;box-sizing:border-box;border:1px solid #ddd;border-radius:6px;padding:6px 8px;margin:4px 0;font-size:12px}
.tm-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tm-hint{color:#999;font-size:11px;margin-top:4px}
.tm-empty{color:#999;text-align:center;padding:14px 0}
.tm-details summary{cursor:pointer;color:#666;font-size:12px;margin:4px 0}
.tm-toggle{width:36px;height:20px;border-radius:10px;background:#ddd;position:relative;cursor:pointer;transition:.15s;flex:0 0 auto}
.tm-toggle.on{background:#34c759}
.tm-toggle::after{content:'';position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;transition:.15s}
.tm-toggle.on::after{left:18px}
.tm-err{color:#d93025;font-size:12px;margin-top:6px}
`;
  const s = document.createElement('style');
  s.id = 'tm-style';
  s.textContent = css;
  document.head.appendChild(s);
}

function _esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function _shortCommit(src) {
  const c = (src && src.commit) || '';
  return c ? c.slice(0, 8) : '';
}

function _render(cat) {
  const tools = cat.tools || [];
  const external = tools.filter(t => t.external);
  const builtin = tools.filter(t => !t.external);
  const allow = cat.git_allowlist || [];

  let html = '';

  html += `<div class="tm-card">
    <h3>安装工具</h3>
    <div class="tm-hint">ZIP：包内需含 manifest.json + main.py；安装后默认禁用，需手动启用。安装期不会执行任何代码。</div>
    <div style="margin-top:8px">
      <input class="tm-input" type="file" id="tm-zip" accept=".zip">
      <label class="tm-hint"><input type="checkbox" id="tm-force"> 覆盖同 id 旧版本</label>
      <button class="tm-btn primary" id="tm-install-zip">上传并安装</button>
    </div>
    <div style="margin-top:10px;border-top:1px dashed #eee;padding-top:8px">
      <div class="tm-hint">Git（需白名单）：${allow.length ? _esc(allow.join(' , ')) : t('tm_no_allowlist')}</div>
      <div class="tm-grid">
        <input class="tm-input" id="tm-git-repo" placeholder="https://github.com/org/sases-tools">
        <input class="tm-input" id="tm-git-ref" placeholder="分支/标签（可空）">
        <input class="tm-input" id="tm-git-sub" placeholder="子目录（可空）">
        <label class="tm-hint"><input type="checkbox" id="tm-git-force"> 覆盖旧版本</label>
      </div>
      <button class="tm-btn primary" id="tm-install-git">从 Git 安装</button>
    </div>
    <div style="margin-top:10px;display:flex;gap:8px;align-items:center">
      <button class="tm-btn" id="tm-admin">管理员 Token</button>
      <span class="tm-hint" id="tm-admin-state">${_adminToken() ? t('tm_configured') : t('tm_not_configured')}</span>
      <span class="tm-err" id="tm-err"></span>
    </div>
  </div>`;

  html += `<div class="tm-card"><h3>外部工具 <span class="tm-badge">${external.length}</span></h3>`;
  if (!external.length) {
    html += `<div class="tm-empty">${t('tm_empty')}</div>`;
  } else {
    external.forEach(t => {
      const src = t.source || {};
      const srcText = src.type === 'git'
        ? `git ${src.repo || ''}${src.commit ? ' @' + _shortCommit(src) : ''}`
        : (src.type === 'zip' ? `zip ${src.filename || ''}` : '');
      html += `<div class="tm-row" data-id="${_esc(t.id)}">
        <div class="tm-main">
          <div class="tm-name">${_esc(t.name || t.id)}<span class="tm-badge ${t.enabled ? '' : 'off'}">${t.enabled ? '已启用' : '已禁用'}</span></div>
          <div class="tm-sub">${_esc(t.id)} · v${_esc(t.version || '?')}${srcText ? ' · ' + _esc(srcText) : ''}</div>
        </div>
        <div class="tm-toggle ${t.enabled ? 'on' : ''}" data-action="toggle" title="启用/禁用"></div>
        <button class="tm-btn danger" data-action="delete">卸载</button>
      </div>`;
    });
  }
  html += '</div>';

  html += `<div class="tm-card">
    <details class="tm-details"><summary>内置工具 <span class="tm-badge">${builtin.length}</span></summary>`;
  builtin.forEach(t => {
    html += `<div class="tm-row"><div class="tm-main">
      <div class="tm-name">${_esc(t.name || t.id)}</div>
      <div class="tm-sub">${_esc(t.id)} · v${_esc(t.version || '?')} · ${_esc(t.description || '')}</div>
    </div></div>`;
  });
  html += '</details></div>';

  _root.innerHTML = html;
  _bind();
}

function _err(msg) {
  const el = document.getElementById('tm-err');
  if (el) el.textContent = msg || '';
}

async function _refresh() {
  try {
    const cat = await _json('/tools/catalog', { headers: _headers(false) });
    _render(cat);
  } catch (e) {
    _root.innerHTML = `<div class="tm-card tm-err">加载失败：${_esc(e.message)}</div>`;
  }
}

function _bind() {
  const zipBtn = document.getElementById('tm-install-zip');
  if (zipBtn) zipBtn.onclick = () => _installZip();
  const gitBtn = document.getElementById('tm-install-git');
  if (gitBtn) gitBtn.onclick = () => _installGit();
  const adminBtn = document.getElementById('tm-admin');
  if (adminBtn) adminBtn.onclick = () => {
    const v = prompt('输入工具市场管理员 Token（保存在本机浏览器）', _adminToken());
    if (v === null) return;
    localStorage.setItem(TOKEN_KEY, v.trim());
    const st = document.getElementById('tm-admin-state');
    if (st) st.textContent = v.trim() ? '已配置' : '未配置';
  };

  _root.querySelectorAll('[data-action="toggle"]').forEach(el => {
    el.onclick = async () => {
      const id = el.closest('.tm-row').dataset.id;
      const on = el.classList.contains('on');
      try {
        await _json(`/tools/${id}/${on ? 'disable' : 'enable'}`, { method: 'POST', headers: _headers(true) });
        await _refresh();
      } catch (e) { _err(e.message); }
    };
  });
  _root.querySelectorAll('[data-action="delete"]').forEach(btn => {
    btn.onclick = async () => {
      const id = btn.closest('.tm-row').dataset.id;
      if (!confirm('确认卸载 ' + id + '？')) return;
      try {
        await _json(`/tools/${id}`, { method: 'DELETE', headers: _headers(true) });
        await _refresh();
      } catch (e) { _err(e.message); }
    };
  });
}

async function _installZip() {
  const input = document.getElementById('tm-zip');
  const file = input && input.files && input.files[0];
  if (!file) { _err('请选择 ZIP 文件'); return; }
  const force = document.getElementById('tm-force').checked;
  const fd = new FormData();
  fd.append('file', file);
  _err('');
  try {
    await _json(`/tools/install/zip?force=${force ? 'true' : 'false'}`,
      { method: 'POST', headers: _headers(true), body: fd });
    await _refresh();
  } catch (e) { _err(e.message); }
}

async function _installGit() {
  const repo = document.getElementById('tm-git-repo').value.trim();
  const ref = document.getElementById('tm-git-ref').value.trim();
  const subpath = document.getElementById('tm-git-sub').value.trim();
  const force = document.getElementById('tm-git-force').checked;
  if (!repo) { _err('请填写仓库地址'); return; }
  _err('');
  try {
    await _json('/tools/install/git', {
      method: 'POST',
      headers: { ..._headers(true), 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo, ref, subpath, force }),
    });
    await _refresh();
  } catch (e) { _err(e.message); }
}

export async function openToolMarket() {
  _css();
  openSubpage('工具市场', '<div id="tool-market-root"><div class="tm-empty">加载中...</div></div>');
  _root = document.getElementById('tool-market-root');
  await _refresh();
}

window.SASES = window.SASES || {};
window.SASES.toolMarket = { open: openToolMarket };
