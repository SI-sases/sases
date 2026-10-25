// static/modules/i18n.js
import { zh } from './i18n_zh.js';
import { en } from './i18n_en.js';

const translations = { zh, en };

let currentLang = localStorage.getItem('sases_lang') || 'zh';

export function t(key) {
  const dict = translations[currentLang] || translations.zh;
  return dict[key] || translations.zh[key] || key;
}

export function setLang(lang) {
  if (!translations[lang]) return;
  currentLang = lang;
  localStorage.setItem('sases_lang', lang);
  // 触发语言变化事件，通知各模块更新界面文本
  window.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
}

export function getLang() {
  return currentLang;
}

// 向后兼容：把 t 挂到 window，供老代码调用
window.t = t;