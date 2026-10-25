// static/modules/auth.js
import { api } from './api.js';

export async function login(username, password) {
  const data = await api.login(username, password);
  const token = data.access_token || data.token;
  if (!token) {
    throw new Error('登录响应缺少 token');
  }
  const _dlBtn = document.getElementById('download-client-btn'); if(_dlBtn) _dlBtn.style.display='none';
  localStorage.setItem('sases_token', token);
  localStorage.setItem('sases_username', username);
  localStorage.setItem('sases_user_id', data.user_id);
  localStorage.setItem('sases_sas_id', data.sases_id || '');
  return data;
}

export async function register(username, password) {
  const data = await api.register(username, password);
  const token = data.access_token || data.token;
  if (!token) {
    throw new Error('注册响应缺少 token');
  }
  const _dlBtn = document.getElementById('download-client-btn'); if(_dlBtn) _dlBtn.style.display='none';
  localStorage.setItem('sases_token', token);
  localStorage.setItem('sases_username', username);
  localStorage.setItem('sases_user_id', data.user_id);
  localStorage.setItem('sases_sas_id', data.sases_id || '');
  return data;
}

export function isLoggedIn() {
  return !!localStorage.getItem('sases_token');
}

export function logout() {
  const _dlBtn2 = document.getElementById('download-client-btn'); if(_dlBtn2) _dlBtn2.style.display='flex';
  localStorage.removeItem('sases_token');
  localStorage.removeItem('sases_username');
  localStorage.removeItem('sases_user_id');
  localStorage.removeItem('sases_sas_id');
  window.location.reload();
}

export function getToken() {
  return localStorage.getItem('sases_token');
}

export function getSasesId() {
  return localStorage.getItem('sases_sas_id') || '';
}