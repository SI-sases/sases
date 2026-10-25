// static/modules/subpage.js

// ==================== 二级页面控制 ====================
export function openSubpage(title, contentHtml, options = {}) {
  const subpageTitle = document.getElementById('subpage-title');
  const subpageContent = document.getElementById('subpage-content');
  if (!subpageTitle || !subpageContent) return;

  window.__currentReturnAction = options.returnAction || null;

  subpageTitle.textContent = title;
  subpageContent.innerHTML = contentHtml;

  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  if (bottomNav) bottomNav.style.display = 'none';
  if (topBar) topBar.style.display = 'none';

  const avatarEl = document.getElementById('subpage-avatar');
  if (avatarEl) {
    if (options.avatarHtml) {
      avatarEl.innerHTML = options.avatarHtml;
      avatarEl.style.display = 'flex';
    } else {
      avatarEl.style.display = 'none';
    }
  }

  const moreBtn = document.getElementById('subpage-more-btn');
  if (moreBtn) {
    if (options.showMore) {
      moreBtn.style.display = 'block';
      moreBtn.onclick = options.onMore || (() => alert('更多操作待实现'));
    } else {
      moreBtn.style.display = 'none';
      moreBtn.onclick = null;
    }
  }

  const rightBtn = document.getElementById('subpage-right-btn');
  if (rightBtn) {
    if (options.rightBtn) {
      rightBtn.textContent = options.rightBtn.text;
      rightBtn.style.display = 'block';
      rightBtn.onclick = options.rightBtn.onclick;
    } else {
      rightBtn.style.display = 'none';
      rightBtn.onclick = null;
    }
  }


  const backBtn = document.getElementById('subpage-back-btn');
  if (backBtn) {
    backBtn.onclick = closeSubpage;
  }

  const subpage = document.getElementById('view-subpage');
  if (subpage) subpage.style.display = 'flex';
}

export function closeSubpage() {
  if (typeof window.__currentReturnAction === 'function') {
    const action = window.__currentReturnAction;
    window.__currentReturnAction = null;
    action();
    return;
  }

  const subpage = document.getElementById('view-subpage');
  if (subpage) subpage.style.display = 'none';
  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  if (bottomNav) bottomNav.style.display = 'flex';
  if (topBar) topBar.style.display = 'flex';
  window.__currentReturnAction = null;
}

// 挂载到全局，供其他模块调用
window.openSubpage = openSubpage;
window.closeSubpage = closeSubpage;