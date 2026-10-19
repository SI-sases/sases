// static/modules/main.js
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

  const goRegister = document.getElementById('go-register');
  if (goRegister) {
    goRegister.addEventListener('click', async (e) => {
      e.preventDefault();
      if (!agreeCheckbox.checked) {
        alert('请先阅读并同意用户协议和隐私政策');
        return;
      }
      const regUser = usernameInput.value.trim();
      const regPass = passwordInput.value;
      if (!regUser || !regPass) {
        alert('请先在上方输入框填写用户名和密码，再点注册');
        usernameInput.focus();
        return;
      }
      try {
        await register(regUser, regPass);
        window.location.reload();
      } catch (err) {
        alert('注册失败: ' + (err.message || err));
      }
    });
  }

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