// static/modules/group_toast.js
// 群聊通用 Toast 提示（从 group_chat.js 模块 3 迁出）

export function showGroupToast(text) {
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed;top:80px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.8);color:#fff;padding:12px 24px;border-radius:10px;font-size:14px;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
  toast.textContent = text;
  document.body.appendChild(toast);
  setTimeout(function() {
    toast.style.transition = 'opacity 0.4s';
    toast.style.opacity = '0';
    setTimeout(function() { toast.remove(); }, 400);
  }, 2000);
}

// 保持全局兼容
window.showGroupToast = showGroupToast;
