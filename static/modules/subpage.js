// static/modules/subpage.js

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
}

export function closeSubpage() {
  const viewSubpage = document.getElementById('view-subpage');
  if (viewSubpage) viewSubpage.classList.remove('active');
  
  const bottomNav = document.querySelector('.bottom-nav');
  const topBar = document.querySelector('.top-bar');
  if (bottomNav) bottomNav.style.display = 'flex';
  if (topBar) topBar.style.display = 'flex';

  window.__currentReturnAction = null;
}

window.openSubpage = openSubpage;
window.closeSubpage = closeSubpage;
