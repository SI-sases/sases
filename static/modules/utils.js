// static/modules/utils.js

/**
 * 初始化下拉刷新
 * @param {HTMLElement} container - 需要监听下拉的容器
 * @param {Function} reloadFn - 重新加载数据的异步函数
 */
export function initPullToRefresh(container, reloadFn) {
  let startY = 0;
  let pulling = false;
  let pullDistance = 0;
  const threshold = 60; // 下拉多少像素触发刷新

  // 创建提示元素
  const indicator = document.createElement('div');
  indicator.className = 'pull-indicator';
  indicator.textContent = '下拉刷新';
  container.parentElement.insertBefore(indicator, container);
  indicator.style.display = 'none';

  container.addEventListener('touchstart', (e) => {
    if (container.scrollTop <= 0) {
      startY = e.touches[0].clientY;
      pulling = true;
    }
  }, { passive: true });

  container.addEventListener('touchmove', (e) => {
    if (!pulling) return;
    const currentY = e.touches[0].clientY;
    pullDistance = currentY - startY;
    if (pullDistance > 0 && container.scrollTop <= 0) {
      indicator.style.display = 'block';
      indicator.textContent = pullDistance >= threshold ? '松开刷新' : '下拉刷新';
      if (pullDistance < threshold) {
        // 阻止默认滚动，显示指示器
        e.preventDefault();
      }
    }
  }, { passive: false });

  container.addEventListener('touchend', async () => {
    if (!pulling) return;
    pulling = false;
    if (pullDistance >= threshold) {
      indicator.textContent = '刷新中...';
      try {
        await reloadFn();
      } catch (e) {
        console.error('刷新失败', e);
      }
    }
    indicator.style.display = 'none';
    pullDistance = 0;
  });
}