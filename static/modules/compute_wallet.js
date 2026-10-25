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
    servicesHtml = '<div class="subpage-placeholder">暂无可用服务</div>';
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
          <span class="menu-value">${s.unit_cost} 算力</span>
        </div>
      `;
    });
    servicesHtml += '</div>';
  }

  let txHtml = '';
  if (transactions.length === 0) {
    txHtml = '<div class="subpage-placeholder">暂无交易记录</div>';
  } else {
    txHtml = '<div class="me-menu">';
    transactions.forEach(tx => {
      const date = new Date(tx.created_at).toLocaleString('zh-CN');
      const isIncome = tx.amount > 0;
      const sign = isIncome ? '+' : '';
      const color = isIncome ? '#34c759' : '#ff3b30';
      const typeText = {
        'recharge': '充值（旧记录）',
        'exchange': '积分兑换',
        'consume': '消费'
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
      <div class="wallet-label">算力余额</div>
      <div class="wallet-balance">${balanceData.balance}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:4px;">
        累计充值 ${balanceData.total_purchased} · 累计消费 ${balanceData.total_consumed}
      </div>
    </div>


    <div class="me-menu">
      <div class="me-menu-item" id="compute-exchange-entry">
        <span class="menu-icon">🔄</span>
        <span class="menu-label">积分兑换算力</span>
        <span class="menu-value">${pricing ? pricing.exchange_rate : '5 积分 = 1 算力'}</span>
        <span class="menu-arrow">›</span>
      </div>
    </div>

    <div class="section-title">官方算力服务</div>
    ${servicesHtml}

    <div class="section-title">交易记录</div>
    ${txHtml}
  `;

  window.openSubpage('算力钱包', contentHtml, {
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
      if (!confirm('是否模拟消费一次该服务？')) return;
      try {
        const res = await api.consumeCompute(key);
        alert(`消费成功，剩余 ${res.balance} 算力`);
        openComputeWallet(returnAction);
      } catch (e) {
        alert('消费失败：' + e.message);
      }
    };
  });
}

// ========== 积分兑换算力页 ==========
function openExchangePage(returnAction) {
  const contentHtml = `
    <div class="me-menu">
      <div class="me-menu-item">
        <span class="menu-label">消耗积分</span>
        <input type="number" id="exchange-credits-input" class="inline-input" placeholder="必须为 5 的倍数" min="5" step="5">
      </div>
      <div class="me-menu-item">
        <span class="menu-label">预计获得</span>
        <span class="menu-value" id="exchange-preview">0 算力</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-label">汇率</span>
        <span class="menu-value">5 积分 = 1 算力</span>
      </div>
      <div class="me-menu-item">
        <span class="menu-label">每日上限</span>
        <span class="menu-value">500 积分</span>
      </div>
    </div>
    <button class="save-btn" id="compute-exchange-confirm">确认兑换</button>
  `;
  window.openSubpage('积分兑换算力', contentHtml, {
    showMore: false,
    returnAction: () => openComputeWallet(returnAction)
  });

  const input = document.getElementById('exchange-credits-input');
  const preview = document.getElementById('exchange-preview');

  input.addEventListener('input', () => {
    const val = parseInt(input.value) || 0;
    const compute = Math.floor(val / 5);
    preview.textContent = `${compute} 算力`;
  });

  document.getElementById('compute-exchange-confirm').onclick = async () => {
    const credits = parseInt(input.value) || 0;
    if (credits <= 0) {
      alert('请输入有效积分数量');
      return;
    }
    if (credits % 5 !== 0) {
      alert('积分必须是 5 的倍数');
      return;
    }
    try {
      const res = await api.exchangeCompute(credits);
      alert(`兑换成功！消耗 ${res.credits_consumed} 积分，获得 ${res.compute_gained} 算力`);
      openComputeWallet(returnAction);
    } catch (e) {
      alert('兑换失败：' + e.message);
    }
  };
}

// 挂载到全局
window.openComputeWallet = openComputeWallet;