// static/modules/market.js
import { api } from './api.js';
import { t } from './i18n.js';

export async function openMarketPage() {
  let ordersHtml = '<div class="subpage-placeholder">加载中...</div>';
  window.openSubpage(t('market'), ordersHtml);

  try {
    const data = await api.listMarketOrders();
    const orders = data.orders || [];
    if (orders.length === 0) {
      ordersHtml = `<div class="subpage-placeholder">${t('no_orders')}</div>`;
    } else {
      ordersHtml = '<div class="me-menu">';
      orders.forEach(order => {
        const typeLabel = order.order_type === 'buy_compute' ? t('buy_compute') : t('sell_compute');
        const statusText = order.status === 'open' ? t('in_progress') : t('completed');
        ordersHtml += `
          <div class="me-menu-item">
            <div class="menu-text">
              <div class="menu-title">${order.description} (${typeLabel})</div>
              <div class="menu-desc">${order.owner_name} · ${order.price}${t('credits')} · ${statusText}</div>
            </div>
            ${order.status === 'open' && order.user_id !== parseInt(localStorage.getItem('sases_user_id') || '0') ? `<button class="accept-order-btn" data-order-id="${order.id}">${t('accept_order')}</button>` : ''}
          </div>
        `;
      });
      ordersHtml += '</div>';
    }
  } catch (e) {
    ordersHtml = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }

  const contentHtml = `
    <div class="market-publish-area">
      <select id="market-order-type" class="market-input">
        <option value="buy_compute">${t('buy_compute')}</option>
        <option value="sell_compute">${t('sell_compute')}</option>
      </select>
      <input type="number" id="market-amount" class="market-input" placeholder="${t('compute_amount')}" min="1">
      <input type="number" id="market-price" class="market-input" placeholder="${t('price_per_compute')}" min="0.01" step="0.01">
      <div style="font-size:13px;color:#666;">${t('total')}: <span id="market-total">0</span> ${t('credits')}</div>
      <button id="market-publish-btn" class="save-btn">${t('publish_order')}</button>
    </div>
    ${ordersHtml}
  `;
  document.getElementById('subpage-content').innerHTML = contentHtml;

  const typeSelect = document.getElementById('market-order-type');
  const amountInput = document.getElementById('market-amount');
  const priceInput = document.getElementById('market-price');
  const totalSpan = document.getElementById('market-total');
  const publishBtn = document.getElementById('market-publish-btn');

  function updateTotal() {
    const amount = parseFloat(amountInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    totalSpan.textContent = (amount * price).toFixed(2);
  }
  amountInput.addEventListener('input', updateTotal);
  priceInput.addEventListener('input', updateTotal);

  publishBtn.addEventListener('click', async () => {
    const order_type = typeSelect.value;
    const amount = parseFloat(amountInput.value);
    const price = parseFloat(priceInput.value);
    if (!amount || amount <= 0 || !price || price <= 0) { alert(t('please_input_all')); return; }
    const description = `${amount} ${t('compute_power')}`;
    try {
      await api.createMarketOrder(order_type, description, amount * price);
      alert(t('publish_success'));
      openMarketPage();
    } catch (e) {
      alert(t('publish_failed') + ': ' + e.message);
    }
  });

  // 绑定接单
  document.querySelectorAll('.accept-order-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const orderId = btn.dataset.orderId;
      if (!confirm(t('confirm_accept_order'))) return;
      try {
        await api.acceptMarketOrder(orderId);
        alert(t('accept_success'));
        openMarketPage();
      } catch (e) {
        alert(t('accept_failed') + ': ' + e.message);
      }
    });
  });
}