// static/modules/main.js
// ====== 智能节点测速分流 ======
async function checkNodeSpeedAndRedirect() {
    // 如果存在 hash 路由（说明可能在做特定操作，比如登录中），就不跳转，防止打断
    if (window.location.hash && window.location.hash.length > 2) return;

    const nodes = [
        { host: '47.96.87.147:8001', protocol: 'http:', name: '国内节点' },
        { host: '8.210.238.165:8443', protocol: 'https:', name: '香港节点' }
    ];
    
    const currentHost = window.location.host;
    let fastestNode = nodes.find(n => currentHost === n.host) || nodes[0];
    let minTime = 9999;

    for (const node of nodes) {
        const start = performance.now();
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000); // 2秒超时
            
            // 用 no-cors 模式测速，不关心返回内容，只测网络连通耗时
            await fetch(`${node.protocol}//${node.host}/static/favicon.svg?t=${Date.now()}`, { 
                mode: 'no-cors',
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            const time = performance.now() - start;
            if (time < minTime) {
                minTime = time;
                fastestNode = node;
            }
        } catch (e) {
            // 节点不通，忽略
        }
    }
    
    // 如果测出的最快节点不是当前访问的节点，自动重定向
    if (fastestNode.host !== currentHost) {
        console.log(`[Node Selector] 自动切换至最优节点: ${fastestNode.name} (${minTime.toFixed(0)}ms)`);
        window.location.href = `${fastestNode.protocol}//${fastestNode.host}/static/index.html${window.location.hash}`;
    } else {
        console.log(`[Node Selector] 当前已是最优节点: ${fastestNode.name} (${minTime.toFixed(0)}ms)`);
    }
}

// 延迟 1.5 秒执行，避免影响网页首次渲染
setTimeout(checkNodeSpeedAndRedirect, 1500);
// ==============================
import { login, register, isLoggedIn } from './auth.js';
import { api } from './api.js';
import { initMessages } from './messages.js';
import { initChat, openChatWindow, closeChatWindow } from './chat.js';
import { initContacts } from './contacts.js';
import { initDiscover } from './discover.js';
import { initMe } from './me.js';
import './me_models.js';
import './me_wallet.js';
import './compute_wallet.js';
import './me_settings.js';
import './me_memory.js';
import './pet.js';
import './base.js';
import './onboarding.js';
import { openSubpage, closeSubpage } from './subpage.js';
import { openGroupChat, closeGroupChat } from './group_chat.js';
import { openGlobalSearch } from './search.js';
import { initSideDrawer } from './sidebar.js';
import { showPlusMenu } from './plus_menu.js';
import { t, setLang, getLang } from './i18n.js';

window.initMe = initMe;

document.addEventListener('DOMContentLoaded', function () {
  var dlBtn = document.getElementById('download-client-btn');
  if (!dlBtn) return;
  dlBtn.addEventListener('click', function (e) {
    e.preventDefault();
    if (document.getElementById('dl-client-modal')) return;
    var mask = document.createElement('div');
    mask.id = 'dl-client-modal';
    mask.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:10000;display:flex;align-items:center;justify-content:center;';
    mask.innerHTML = '<div style="background:#fff;border-radius:10px;padding:24px;max-width:420px;width:90%;box-shadow:0 8px 30px rgba(0,0,0,.2);">' +
      '<h3 style="margin:0 0 12px;font-size:18px;">下载 SASES 桌面客户端</h3>' +
      '<ol style="margin:0 0 16px;padding-left:20px;line-height:1.9;font-size:14px;color:#333;">' +
      '<li>下载并解压 zip</li>' +
      '<li>双击运行“启动SASES.bat”</li>' +
      '<li>首次运行按提示输入 API Key</li>' +
      '</ol>' +
      '<a href="https://8.210.238.165:8443/downloads/sases-portable.zip" style="display:block;text-align:center;background:#2563eb;color:#fff;padding:10px;border-radius:6px;text-decoration:none;font-size:14px;">下载 Windows 绿色版 (v1.0)</a>' +
      '<button id="dl-client-close" style="margin-top:12px;width:100%;background:#eee;border:none;padding:8px;border-radius:6px;cursor:pointer;">关闭</button>' +
      '</div>';
    document.body.appendChild(mask);
    document.getElementById('dl-client-close').onclick = function () { mask.remove(); };
    mask.addEventListener('click', function (ev) { if (ev.target === mask) mask.remove(); });
  });
});

document.addEventListener('DOMContentLoaded', () => {
  window.currentGroupChat = false;
  applyLanguage();
  initLoginUI();
  initBottomNav();
  initTopActions();
  initChat();
  initSideDrawer();
  checkAuthState();
});

function applyLanguage() {
  const lang = getLang();
  const isEn = lang === 'en';

  // ========== 登录界面 ==========
  const loginTitle = document.getElementById('login-title');
  if (loginTitle) loginTitle.textContent = t('login_title');
  const loginSubtitle = document.getElementById('login-subtitle');
  if (loginSubtitle) loginSubtitle.textContent = t('login_subtitle');
  const loginUsername = document.getElementById('login-username');
  if (loginUsername) loginUsername.placeholder = t('login_username_placeholder');
  const loginPassword = document.getElementById('login-password');
  if (loginPassword) loginPassword.placeholder = t('login_password_placeholder');
  const loginBtn = document.getElementById('login-btn');
  if (loginBtn) loginBtn.textContent = t('login_button');

  // 注册 / 找回密码
  const goRegister = document.getElementById('go-register');
  if (goRegister) goRegister.textContent = isEn ? 'Register' : '注册新账号';
  const forgotPassword = document.getElementById('forgot-password');
  if (forgotPassword) forgotPassword.textContent = isEn ? 'Forgot Password' : '找回密码';

  // 用户协议行
  const agreementText = document.getElementById('agreement-text');
  if (agreementText) {
    const userAgreementLink = document.getElementById('user-agreement-link');
    const privacyPolicyLink = document.getElementById('privacy-policy-link');
    if (userAgreementLink) userAgreementLink.textContent = isEn ? 'User Agreement' : '用户协议';
    if (privacyPolicyLink) privacyPolicyLink.textContent = isEn ? 'Privacy Policy' : '隐私政策';
    agreementText.innerHTML = isEn
      ? `I have read and agree to <a href="#" id="user-agreement-link">User Agreement</a> and <a href="#" id="privacy-policy-link">Privacy Policy</a>`
      : `我已阅读并同意 <a href="#" id="user-agreement-link">用户协议</a> 和 <a href="#" id="privacy-policy-link">隐私政策</a>`;
  }

  // ========== 底部导航 ==========
  document.querySelectorAll('.nav-btn').forEach(btn => {
    const view = btn.dataset.view;
    if (view === 'messages') btn.textContent = t('nav_messages');
    else if (view === 'contacts') btn.textContent = t('nav_contacts');
    else if (view === 'discover') btn.textContent = t('nav_discover');
    else if (view === 'me') btn.textContent = t('nav_me');
  });

  // ========== 顶部标题 ==========
  const activeView = document.querySelector('.nav-btn.active')?.dataset.view;
  if (activeView) {
    const titles = {
      messages: t('nav_messages'),
      contacts: t('nav_contacts'),
      discover: t('nav_discover'),
      me: t('nav_me')
    };
    const topTitle = document.getElementById('top-title');
    if (topTitle) topTitle.textContent = titles[activeView] || 'SASES';
  }
}

function initLoginUI() {
  const loginBtn = document.getElementById('login-btn');
  const usernameInput = document.getElementById('login-username');
  const passwordInput = document.getElementById('login-password');
  const agreeCheckbox = document.getElementById('agree-checkbox');
  const langButtons = document.querySelectorAll('.lang-btn');

  if (!loginBtn || !usernameInput || !passwordInput || !agreeCheckbox) return;

  function showLoginForm(name) {
    document.querySelectorAll('.login-form').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('form-' + name);
    if (target) target.classList.add('active');
  }

  const goRegister = document.getElementById('go-register');
  if (goRegister) goRegister.addEventListener('click', (e) => { e.preventDefault(); showLoginForm('register'); });

  const goForgot = document.getElementById('forgot-password');
  if (goForgot) goForgot.addEventListener('click', (e) => { e.preventDefault(); showLoginForm('reset'); });

  const regBack = document.getElementById('reg-back');
  if (regBack) regBack.addEventListener('click', (e) => { e.preventDefault(); showLoginForm('login'); });

  const resetBack = document.getElementById('reset-back');
  if (resetBack) resetBack.addEventListener('click', (e) => { e.preventDefault(); showLoginForm('login'); });

  const regSubmit = document.getElementById('reg-submit');
  if (regSubmit) regSubmit.addEventListener('click', async () => {
    const u = document.getElementById('reg-username').value.trim();
    const p = document.getElementById('reg-password').value;
    const p2 = document.getElementById('reg-password2').value;
    const em = document.getElementById('reg-email').value.trim();
    if (!u || !p) { alert('用户名和密码不能为空'); return; }
    if (p !== p2) { alert('两次输入的密码不一致'); return; }
    try {
      const res = await fetch('/auth/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: u, password: p, email: em || null }) });
      const data = await res.json();
      if (!res.ok) { const msg = data.error || data.message || (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail) || '注册失败'; alert(msg); return; }
      localStorage.setItem('sases_token', data.access_token);
      localStorage.setItem('sases_username', data.username);
      localStorage.setItem('sases_user_id', data.user_id);
      localStorage.setItem('sases_sas_id', data.sases_id || '');
      window.location.reload();
    } catch (err) { alert('网络错误: ' + err.message); }
  });

  const resetSubmit = document.getElementById('reset-submit');
  if (resetSubmit) resetSubmit.addEventListener('click', async () => {
    const u = document.getElementById('reset-username').value.trim();
    const em = document.getElementById('reset-email').value.trim();
    const p = document.getElementById('reset-password').value;
    if (!u || !em || !p) { alert('所有字段都必须填写'); return; }
    try {
      const res = await fetch('/auth/reset-password', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: u, email: em, new_password: p }) });
      const data = await res.json();
      if (!res.ok) { const msg = data.error || data.message || (Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail) || '重置失败'; alert(msg); return; }
      alert(data.message || '密码已重置，请用新密码登录');
      showLoginForm('login');
    } catch (err) { alert('网络错误: ' + err.message); }
  });

  langButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      setLang(lang);
      applyLanguage();
      langButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  loginBtn.addEventListener('click', async () => {
    if (!agreeCheckbox.checked) {
      alert('请先阅读并同意用户协议和隐私政策');
      return;
    }
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    if (!username || !password) {
      alert('请输入用户名和密码');
      return;
    }
    try {
      await login(username, password);
      enterMainApp();
    } catch (e) {
      alert('登录失败：' + e.message);
    }
  });

  passwordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loginBtn.click();
  });
}

function checkAuthState() {
  if (isLoggedIn()) {
    enterMainApp();
  } else {
    showLogin();
  }
}

function showLogin() {
  document.getElementById('view-login').style.display = 'flex';
  document.getElementById('main-app').style.display = 'none';
}

function enterMainApp() {
  document.getElementById('view-login').style.display = 'none';
  document.getElementById('main-app').style.display = 'flex';
  activateMainView('messages');
  import('./ws_client.js').then(m => m.connectUserWs()).catch(() => {});
}

function activateMainView(viewName) {
  closeChatWindow();
  window.__currentReturnAction = null;
  closeSubpage();

  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.view === viewName));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(`view-${viewName}`);
  if (target) target.classList.add('active');

  const titles = {
    messages: t('nav_messages'),
    contacts: t('nav_contacts'),
    discover: t('nav_discover'),
    me: t('nav_me')
  };
  const topTitle = document.getElementById('top-title');
  if (topTitle) topTitle.textContent = titles[viewName] || 'SASES';

  const topLeft = document.getElementById('top-left');
  if (topLeft) {
    topLeft.style.display = viewName === 'messages' ? 'flex' : 'none';
  }

  const topActions = document.getElementById('top-actions');
  if (topActions) {
    topActions.style.display = viewName !== 'me' ? 'flex' : 'none';
  }

  if (viewName === 'messages') initMessages();
  if (viewName === 'contacts') initContacts();
  if (viewName === 'discover') initDiscover();
  if (viewName === 'me') initMe();
}

function initBottomNav() {
  const nav = document.querySelector('.bottom-nav');
  if (!nav) return;
  nav.addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-btn');
    if (!btn) return;
    activateMainView(btn.dataset.view);
  });
}

function initTopActions() {
  const searchBtn = document.getElementById('top-search-btn');
  const plusBtn = document.getElementById('top-plus-btn');
  if (searchBtn) searchBtn.addEventListener('click', openGlobalSearch);
  if (plusBtn) plusBtn.addEventListener('click', showPlusMenu);
}