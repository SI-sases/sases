// static/modules/i18n.js
// 单一 i18n 系统：zh / en 两套字典，t() 只查当前语言，英文缺 key 不回退中文。
import { zh } from './i18n_zh.js';
import { en } from './i18n_en.js';

const translations = { zh, en };
const STORAGE_KEY = 'sases_lang';
const SUPPORTED = ['zh', 'en'];

// 浏览器语言 -> 支持的语言（中文环境用 zh，其他一律 en）
function detectBrowserLang() {
  const list = (navigator.languages && navigator.languages.length)
    ? navigator.languages
    : [navigator.language || navigator.userLanguage || ''];
  for (const raw of list) {
    const l = String(raw || '').toLowerCase();
    if (!l) continue;
    if (l.startsWith('zh')) return 'zh';
    if (l.startsWith('en')) return 'en';
  }
  return 'en';
}

// 默认语言：localStorage.sases_lang 优先，其次浏览器语言
function resolveInitialLang() {
  let saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { saved = null; }
  if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
  return detectBrowserLang();
}

let currentLang = resolveInitialLang();

// 同步 <html lang>，并标记已应用的语言（供 CSS 兜底）
function syncDocumentLang(lang) {
  if (typeof document === 'undefined' || !document.documentElement) return;
  document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : 'zh-CN');
  document.documentElement.setAttribute('data-lang', lang);
}

// 首屏尽早同步，避免 html lang 与界面语言不一致
syncDocumentLang(currentLang);

export function t(key) {
  const dict = translations[currentLang] || translations.en;
  const val = dict[key];
  if (typeof val === 'string' && val !== '') return val;
  // 当前语言缺 key：显示 key 本身，便于发现漏翻（不回退中文）
  return key;
}

export function setLang(lang) {
  if (SUPPORTED.indexOf(lang) === -1) return;
  if (lang === currentLang) return; // 语言未变化，不重复广播
  currentLang = lang;
  try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* 隐私模式下忽略 */ }
  syncDocumentLang(lang);
  // 触发语言变化事件，通知各模块更新界面文本
  window.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
}
export function getLang() {
  return currentLang;
}

// 向后兼容：把 t 挂到 window，供老代码调用
window.t = t;
