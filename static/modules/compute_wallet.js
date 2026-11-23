// static/modules/compute_wallet.js
import { api } from './api.js';

// ========== 算力钱包主页 ==========
export async function openComputeWallet(returnAction) {
  let balanceData = { balance: 0, total_purchased: 0, total_consumed: 0 };
  let pricing = null;
  let services = [];
  let transactions = [];

  try {
    balanceData = await api.getComputeBalance();
    pricing = await api.getComputePricing();
    const servicesResp = await api.listComputeServices();
    services = servicesResp.services || [];
    const txResp = await api.getComputeTransactions(20);
    transactions = txResp.transactions || [];
  } catch (e) {
    console.warn('加载算力数据失败', e);
  }

  let servicesHtml = '';
  if (services.length === 0) {
    servicesHtml = `<div class="subpage-placeholder">${t('cwal_no_services')}</div>`;
  } else {
    servicesHtml = '<div class="me-menu">';
    services.forEach(s => {
      servicesHtml += `
        <div class="me-menu-item compute-service-item" data-service-key="${s.service_key}">
          <span class="menu-icon">⚡</span>
          <div class="menu-text">
            <div class="menu-title">${s.service_name}</div>
            <div class="menu-desc">${s.description || ''}</div>
          </div>
          <span class="menu-value">${s.unit_cost} ${t('cwx_compute')}</span>
        </div>
      `;
    });
    servicesHtml += '</div>';
  }

  let txHtml = '';
  if (transactions.length === 0) {
    txHtml = `<div class="subpage-placeholder">${t('cwal_no_tx')}</div>`;
  } else {
    txHtml = '<div class="me-menu">';
    transactions.forEach(tx => {
      const date = new Date(tx.created_at).toLocaleString('zh-CN');
      const isIncome = tx.amount > 0;
      const sign = isIncome ? '+' : '';
      const color = isIncome ? '#34c759' : '#ff3b30';
      const typeText = {
        'recharge': t('cwal_tx_recharge'),
        'exchange': t('cwal_tx_exchange'),
        'consume': t('cwal_tx_consume')
      }[tx.tx_type] || tx.tx_type;
      txHtml += `
        <div class="me-menu-item">
          <div class="menu-text">
            <div class="menu-title">${typeText} ${tx.service_key ? '· ' + tx.service_key : ''}</div>
            <div class="menu-desc">${tx.detail || ''} · ${date}</div>
          </div>
          <span class="menu-value" style="color:${color};">${sign}${tx.amount}</span>
        </div>
      `;
    });
    txHtml += '</div>';
  }


  const contentHtml = `
    <div class="wallet-card" style="background: linear-gradient(135deg, #667eea, #764ba2);">
      <div class="wallet-label">${t('cwx_balance')}</div>
      <div class="wallet-balance">${balanceData.balance}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">
        ${t('cwx_total_purchased')} ${balanceData.total_purchased} · ${t('cwx_total_consumed')} ${balanceData.total_consumed}
      </div>
    </div>


    <div class="me-menu">
      <div class="me-menu-item" id="compute-exchange-entry">
        <span class="menu-icon">🔄</span>
        <span class="menu-label">${t('cwx_exchange')}</span>
        <span class="menu-value">${pricing ? pricing.exchange_rate : t('cwal_rate_fallback')}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>

    <div class="section-title">${t('cwx_official_services')}</div>
    ${servicesHtml}

    <div class="section-title">${t('cwx_tx_history')}</div>
    ${txHtml}
  `;

  window.openSubpage(t('cwal_title'), contentHtml, {
    showMore: false,
    returnAction: returnAction
  });


  const exchangeEntry = document.getElementById('compute-exchange-entry');
  if (exchangeEntry) {
    exchangeEntry.onclick = () => {
      openExchangePage(returnAction);
    };
  }

  document.querySelectorAll('.compute-service-item').forEach(item => {
    item.onclick = async () => {
      const key = item.dataset.serviceKey;
      if (!confirm(t('cwal_simulate_confirm'))) return;
      try {
        const res = await api.consumeCompute(key);
        alert(`${t('cwx_consume_ok')} ${res.balance} ${t('cwx_compute')}`);
        openComputeWallet(returnAction);
      } catch (e) {
        alert(t('cwal_consume_failed') + e.message);
      }
    };
  });
}

// ========== 积分兑换算力页 ==========
function openExchangePage(returnAction) {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">${t('cwx_credits_spend')}</span>
        <input type="number" id="exchange-credits-input" class="inline-input" placeholder="${t('cwx_multiple_ph')}" min="5" step="5">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('cwx_expected')}</span>
        <span class="menu-value" id="exchange-preview">${t('cwx_zero_compute')}</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('cwx_rate')}</span>
        <span class="menu-value">${t('cwx_rate_value')}</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-label">${t('cwx_daily_limit')}</span>
        <span class="menu-value">${t('cwx_daily_limit_value')}</span>
      </div>
    </div>
    <button class="save-btn" id="compute-exchange-confirm">${t('cwx_confirm_exchange')}</button>
  `;
  window.openSubpage(t('cwal_exchange_title'), contentHtml, {
    showMore: false,
    returnAction: () => openComputeWallet(returnAction)
  });

  const input = document.getElementById('exchange-credits-input');
  const preview = document.getElementById('exchange-preview');

  input.addEventListener('input', () => {
    const val = parseInt(input.value) || 0;
    const compute = Math.floor(val / 5);
    preview.textContent = `${compute} ${t('cwx_compute')}`;
  });

  document.getElementById('compute-exchange-confirm').onclick = async () => {
    const credits = parseInt(input.value) || 0;
    if (credits <= 0) {
      alert(t('cwal_points_required'));
      return;
    }
    if (credits % 5 !== 0) {
      alert(t('cwal_points_multiple'));
      return;
    }
    try {
      const res = await api.exchangeCompute(credits);
      alert(`${t('cwx_exchange_ok')} ${res.credits_consumed} · ${res.compute_gained} ${t('cwx_compute')}`);
      openComputeWallet(returnAction);
    } catch (e) {
      alert(t('cwal_exchange_failed') + e.message);
    }
  };
}

// 挂载到全局
window.openComputeWallet = openComputeWallet;