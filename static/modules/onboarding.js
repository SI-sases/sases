// static/modules/onboarding.js
import { api } from './api.js';

let cachedStatus = null;

// 获取引导状态
export async function fetchOnboardingStatus() {
  try {
    const data = await api.getOnboardingStatus();
    cachedStatus = data;
    return data;
  } catch (e) {
    console.warn('获取引导状态失败', e);
    return null;
  }
}

// 上报完成某个动作
export async function reportOnboardingAction(action) {
  if (!cachedStatus || cachedStatus.is_finished) return;
  try {
    const data = await api.completeOnboardingStep(action);
    if (data.advanced) {
      cachedStatus = null;
      showOnboardingToast(data);
    }
  } catch (e) {
    console.warn('上报引导动作失败', e);
  }
}

// 显示引导卡片（在消息页顶部）
export async function renderOnboardingCard() {
  const status = await fetchOnboardingStatus();
  if (!status || status.is_finished) return;

  const container = document.getElementById('messages-list');
  if (!container) return;

  const existing = document.getElementById('onboarding-card');
  if (existing) existing.remove();

  const step = status.current_step;
  if (!step) return;

  const card = document.createElement('div');
  card.id = 'onboarding-card';
  card.style.background = 'linear-gradient(135deg, #e3f2fd, #f3e5f5)';
  card.style.borderRadius = '12px';
  card.style.padding = '14px 16px';
  card.style.margin = '12px';
  card.style.position = 'relative';
  card.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="font-size:28px;">🎯</div>
      <div style="flex:1;">
        <div style="font-size:12px;color:#666;">新手引导 · 第 ${status.current_day} 天 / 共 7 天</div>
        <div style="font-size:15px;font-weight:600;margin-top:2px;">${step.title}</div>
        <div style="font-size:13px;color:#555;margin-top:4px;">${step.desc}</div>
        <div style="font-size:12px;color:#007aff;margin-top:4px;">💡 ${step.hint}</div>
      </div>
    </div>
    <div style="margin-top:10px;background:#fff;border-radius:6px;height:6px;overflow:hidden;">
      <div style="width:${(status.current_day - 1) / 7 * 100}%;height:100%;background:#007aff;transition:width 0.3s;"></div>
    </div>
    <button id="onboarding-dismiss" style="position:absolute;top:8px;right:10px;background:none;border:none;font-size:18px;color:#999;cursor:pointer;">×</button>
  `;

  container.insertBefore(card, container.firstChild);

  document.getElementById('onboarding-dismiss').onclick = () => {
    card.remove();
  };
}

// 完成提示 Toast
function showOnboardingToast(data) {
  const toast = document.createElement('div');
  toast.style.position = 'fixed';
  toast.style.top = '80px';
  toast.style.left = '50%';
  toast.style.transform = 'translateX(-50%)';
  toast.style.background = '#34c759';
  toast.style.color = '#fff';
  toast.style.padding = '12px 20px';
  toast.style.borderRadius = '10px';
  toast.style.zIndex = '9999';
  toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
  toast.style.textAlign = 'center';
  toast.style.fontSize = '14px';
  toast.innerHTML = `
    <div style="font-size:20px;margin-bottom:4px;">🎉</div>
    <div>${data.message}</div>
    ${data.next_step ? `<div style="font-size:12px;margin-top:6px;opacity:0.9;">下个任务：${data.next_step.title}</div>` : ''}
  `;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.5s';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}

// 挂载到全局
window.onboarding = {
  fetchStatus: fetchOnboardingStatus,
  report: reportOnboardingAction,
  renderCard: renderOnboardingCard
};