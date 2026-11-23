// static/modules/discover.js
import { api } from './api.js';
import { t } from './i18n.js';

let initialized = false;

export function initDiscover() {
  if (initialized) return;
  initialized = true;

  const container = document.getElementById('discover-content');
  if (!container) return;

  renderDiscoverEntries(container);

  window.addEventListener('langchange', () => {
    renderDiscoverEntries(container);
  });
}

function renderDiscoverEntries(container) {
  const entries = [
    { icon: '🌌', title: t('wisdom_space'), desc: t('discover_wisdom_desc'), action: 'wisdom' },
    { icon: '🌐', title: t('ai_circle'), desc: t('ai_moments'), action: 'ai-circle' },
    { icon: '📷', title: t('scan'), desc: t('scan_qr_or_seed'), action: 'scan' },
    { icon: '🏆', title: t('leaderboard'), desc: t('contribution_rank'), action: 'leaderboard' },
    { icon: '🧠', title: t('ai_agents'), desc: t('agent_market'), action: 'agents' }
  ];

  let html = `<div class="me-menu">`;
  entries.forEach(entry => {
    html += `
      <div class="me-menu-item" data-entry="${entry.title}" data-action="${entry.action}">
        <span class="menu-icon">${entry.icon}</span>
        <div class="menu-text">
          <div class="menu-title">${entry.title}</div>
          <div class="menu-desc">${entry.desc}</div>
        </div>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;

  container.querySelectorAll('[data-entry]').forEach(item => {
    item.addEventListener('click', () => {
      const action = item.dataset.action;
      const title = item.dataset.entry;
      if (action === 'wisdom') {
        openWisdomMap();
      } else if (action === 'ai-circle') {
        openAiCircle(title);
      } else if (action === 'leaderboard') {
        openLeaderboard(title);
      } else {
        window.openSubpage(title, `<div class="subpage-placeholder">${t('coming_soon')}</div>`);
      }
    });
  });
}

// ==================== 智维空间地图 ====================
async function openWisdomMap() {
  if (typeof window.onboarding?.report === 'function') {
    window.onboarding.report('open_wisdom');
  }

  const mapData = await loadMapData();

  const html = `
    <div class="wisdom-map">
      <div class="map-header">
        <div class="map-stat">
          <span class="map-stat-label">${t('discover_points')}</span>
          <span class="map-stat-value" id="map-credits">${mapData.credits}</span>
        </div>
        <div class="map-stat">
          <span class="map-stat-label">${t('discover_refresh')}</span>
          <span class="map-stat-value" id="map-refresh-timer">--:--</span>
        </div>
      </div>
      
      <div class="map-canvas" id="map-canvas">
        <div class="map-ring map-ring-near"></div>
        <div class="map-ring map-ring-mid"></div>
        <div class="map-ring map-ring-far"></div>
        <div class="map-ring map-ring-remote"></div>
        
        <div class="map-yunchong-node" id="map-yunchong-node">
          <div class="map-yunchong-icon">🎮</div>
          <div class="map-yunchong-label">${t('discover_yunchong_battle')}</div>
        </div>
        
        <div class="map-user">
          <div class="map-user-avatar">😊</div>
        </div>
        
        <div id="map-nodes-container"></div>
      </div>
      
      <div class="map-legend">
        <span class="legend-item"><span class="legend-dot near"></span>0-100m</span>
        <span class="legend-item"><span class="legend-dot mid"></span>100-500m</span>
        <span class="legend-item"><span class="legend-dot far"></span>500m-1km</span>
        <span class="legend-item"><span class="legend-dot remote"></span>1km+</span>
      </div>
    </div>
  `;

  window.openSubpage(t('wisdom_space'), html, { showMore: false });

  renderMapNodes(mapData);
  startRefreshCountdown(mapData.next_refresh_seconds);

  document.getElementById('map-yunchong-node').onclick = () => openYunchongCamp();
}

async function loadMapData() {
  let credits = 0;
  let tasks = [];
  let refreshInfo = { next_refresh_seconds: 900 };

  try {
    const balanceData = await api.getBalance();
    credits = Math.floor(balanceData.balance || 0);
  } catch (e) {
    console.warn('加载积分失败', e);
  }

  try {
    const tasksData = await api.listYunchongTasks();
    tasks = tasksData.tasks || [];
  } catch (e) {
    console.warn('加载任务失败', e);
  }

  try {
    const refreshData = await api.getYunchongRefreshInfo();
    refreshInfo = refreshData;
  } catch (e) {
    console.warn('加载刷新信息失败', e);
  }

  return { credits, tasks, next_refresh_seconds: refreshInfo.next_refresh_seconds || 900 };
}

const RING_RADIUS = {
  near: 42,
  mid: 78,
  far: 114,
  remote: 150
};

function getTaskRing(distance) {
  if (distance <= 100) return 'near';
  if (distance <= 500) return 'mid';
  if (distance <= 1000) return 'far';
  return 'remote';
}

function renderMapNodes(mapData) {
  const container = document.getElementById('map-nodes-container');
  if (!container) return;

  container.innerHTML = '';

  if (mapData.tasks.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'map-empty-hint';
    empty.textContent = t('discover_no_tasks');
    container.appendChild(empty);
    return;
  }

  const ringCounters = { near: 0, mid: 0, far: 0, remote: 0 };
  const ringTotals = { near: 0, mid: 0, far: 0, remote: 0 };
  mapData.tasks.forEach(t => {
    const ring = getTaskRing(t.distance_meters);
    ringTotals[ring]++;
  });

  mapData.tasks.forEach(task => {
    const ring = getTaskRing(task.distance_meters);
    const radius = RING_RADIUS[ring];
    const index = ringCounters[ring]++;
    const total = ringTotals[ring];

    const baseAngle = (index / Math.max(total, 1)) * 360;
    const angleOffset = (task.id * 17) % 40 - 20;
    const angle = baseAngle + angleOffset;
    const rad = angle * Math.PI / 180;

    const x = Math.cos(rad) * radius;
    const y = Math.sin(rad) * radius;

    const node = document.createElement('div');
    node.className = `map-node map-node-${ring}`;
    node.style.left = `calc(50% + ${x}px)`;
    node.style.top = `calc(50% + ${y}px)`;
    node.dataset.taskId = task.id;

    const rarityColor = getRarityColor(task.pet_level);

    node.innerHTML = `
      <div class="map-node-icon" style="border-color:${rarityColor};"></div>
    `;

    node.onclick = (e) => {
      e.stopPropagation();
      openTaskPreview(task);
    };

    container.appendChild(node);
  });
}

function openTaskPreview(task) {
  const rarityColor = getRarityColor(task.pet_level);
  const diffLabel = { low: t('difficulty_low'), medium: t('difficulty_medium'), high: t('difficulty_high') }[task.difficulty] || task.difficulty;
  const energyText = task.energy_cost > 0 ? t('discover_energy_cost').replace('{n}', task.energy_cost) : t('discover_free');

  const html = `
    <div class="task-preview">
      <div class="task-preview-header">
        <div class="task-preview-icon" style="border-color:${rarityColor};">🐾</div>
        <div class="task-preview-title">${task.title}</div>
      </div>
      
      <div class="task-preview-info">
        <div class="task-preview-row">
          <span class="task-preview-label">${t('discover_distance')}</span>
          <span class="task-preview-value">${task.distance_meters} ${t('unit_meter')}</span>
        </div>
        <div class="task-preview-row">
          <span class="task-preview-label">${t('discover_difficulty')}</span>
          <span class="task-preview-value">${diffLabel}</span>
        </div>
        <div class="task-preview-row">
          <span class="task-preview-label">${t('discover_rescuable')}</span>
          <span class="task-preview-value" style="color:${rarityColor};">${t('discover_pet_level').replace('{n}', task.pet_level)}</span>
        </div>
        <div class="task-preview-row">
          <span class="task-preview-label">${t('discover_cost')}</span>
          <span class="task-preview-value">${energyText}</span>
        </div>
      </div>
      
      <div class="task-preview-desc">
        ${task.detail || t('discover_no_detail')}
      </div>
      
      <div class="task-preview-actions">
        <button class="task-preview-btn-cancel" id="task-preview-cancel">${t('cancel')}</button>
        <button class="task-preview-btn-start" id="task-preview-start">${t('discover_start_rescue')}</button>
      </div>
    </div>
  `;

  window.openSubpage(t('discover_task_detail'), html, {
    showMore: false,
    returnAction: () => openWisdomMap()
  });

  document.getElementById('task-preview-cancel').onclick = () => {
    window.closeSubpage();
  };

  document.getElementById('task-preview-start').onclick = async () => {
    const startBtn = document.getElementById('task-preview-start');
    startBtn.disabled = true;
    startBtn.textContent = t('discover_processing');

    try {
      const result = await api.acceptYunchongTask(task.id);
      if (!result.success) {
        alert(result.message || t('discover_cannot_accept'));
        startBtn.disabled = false;
        startBtn.textContent = t('discover_start_rescue');
        return;
      }

      openYunchongRescue(task.id);
    } catch (e) {
      alert(t('discover_op_failed') + e.message);
      startBtn.disabled = false;
      startBtn.textContent = t('discover_start_rescue');
    }
  };
}

// ==================== 抓宠页面 ====================
async function openYunchongRescue(taskId) {
  let task = null;
  let agents = [];
  let usage = null;

  try {
    task = await api.getYunchongTask(taskId);
  } catch (e) {
    alert(t('discover_load_task_failed') + e.message);
    return;
  }

  try {
    const agentsResp = await api.listMyAgents();
    agents = agentsResp.agents || [];
  } catch (e) {
    console.warn('加载智能体失败', e);
  }

  try {
    usage = await api.getYunchongOfficialUsage();
  } catch (e) {
    console.warn('加载官方助手信息失败', e);
  }

  const rarityColor = getRarityColor(task.pet_level);
  const diffLabel = { low: t('ds_low'), medium: t('ds_medium'), high: t('ds_high') }[task.difficulty] || task.difficulty;
  const attempts = task.attempts || 0;
  const isGuaranteeNext = attempts >= 3;

  const remainingFree = usage ? usage.remaining_free : 3;
  const needPay = usage ? usage.need_pay : false;

  let officialDesc = `${t('dst_free_left')}${remainingFree}/3 ${t('dst_times')}`;
  if (needPay) {
    officialDesc += ` · ${t('dst_extra_cost')}`;
  }

  let agentOptionsHtml = `
    <div class="agent-option-item selected" data-agent-id="" data-official="1">
      <div class="agent-option-icon">🎓</div>
      <div class="agent-option-info">
        <div class="agent-option-name">${t('dst_official')}</div>
        <div class="agent-option-desc">${officialDesc}</div>
      </div>
      <div class="agent-option-check">✓</div>
    </div>
  `;
  agents.forEach(agent => {
    agentOptionsHtml += `
      <div class="agent-option-item" data-agent-id="${agent.agent_id}" data-official="0">
        <div class="agent-option-icon">🤖</div>
        <div class="agent-option-info">
          <div class="agent-option-name">${agent.name}</div>
          <div class="agent-option-desc">${agent.description || t('ds_my_agent')}</div>
        </div>
        <div class="agent-option-check">✓</div>
      </div>
    `;
  });

  const guaranteeHint = isGuaranteeNext
    ? `<div style="background:#e8f5e9;color:#2e7d32;padding:10px 12px;border-radius:8px;margin:0 12px 12px;font-size:13px;">✨ ${t('dst_tried')} ${attempts} ${t('dst_times')}, ${t('dst_guarantee')}</div>`
    : '';

  const html = `
    <div class="rescue-detail-header">
      <div class="rescue-pet-icon" style="border-color:${rarityColor};">🐾</div>
      <div class="rescue-pet-info">
        <div class="rescue-task-title">${task.title}</div>
        <div class="rescue-task-meta">${t('dst_difficulty')}${diffLabel} · ${t('dst_distance')}${task.distance_meters}${t('unit_meter')} · ${t('dst_rescuable')}<span style="color:${rarityColor};">${task.pet_level} ${t('dst_level_pet')}</span></div>
      </div>
    </div>

    ${guaranteeHint}

    <div class="section-title">${t('dst_task_desc')}</div>
    <div class="rescue-detail-desc">
      ${task.detail || t('ds_no_detail')}
    </div>

    <div class="section-title">${t('dst_choose_agent')}</div>
    <div class="agent-options" id="agent-options">
      ${agentOptionsHtml}
    </div>

    <div id="rescue-process-container"></div>

    <div style="padding:12px;display:flex;gap:8px;">
      <button class="save-btn" id="rescue-start-btn" style="flex:2;padding:14px;font-size:15px;">🐾 ${t('dst_start')}</button>
      <button id="rescue-abandon-btn" style="flex:1;padding:14px;font-size:14px;background:#f5f5f5;color:#ff3b30;border:none;border-radius:8px;">${t('discover_abandon')}</button>
    </div>
  `;

  window.openSubpage(t('ds_task_title'), html, {
    showMore: false,
    returnAction: () => openWisdomMap()
  });

  let selectedAgentId = null;
  let useOfficial = true;

  document.querySelectorAll('.agent-option-item').forEach(item => {
    item.onclick = () => {
      if (item.classList.contains('disabled')) return;
      document.querySelectorAll('.agent-option-item').forEach(i => i.classList.remove('selected'));
      item.classList.add('selected');
      selectedAgentId = item.dataset.agentId || null;
      useOfficial = item.dataset.official === '1';
    };
  });

  let lastFailureReason = null;

  document.getElementById('rescue-start-btn').onclick = async () => {
    const startBtn = document.getElementById('rescue-start-btn');
    const abandonBtn = document.getElementById('rescue-abandon-btn');
    startBtn.disabled = true;
    abandonBtn.disabled = true;
    startBtn.textContent = t('ds_rescuing');
    document.querySelectorAll('.agent-option-item').forEach(i => i.classList.add('disabled'));

    const processContainer = document.getElementById('rescue-process-container');
    processContainer.innerHTML = '';

    try {
      const analyzeLabel = lastFailureReason ? t('ds_reanalyzing') : t('ds_analyzing');
      addProcessStep(processContainer, 'analyzing', analyzeLabel);

      const analyzeResult = await api.analyzeYunchongTask(
        taskId, selectedAgentId, lastFailureReason, useOfficial
      );

      if (!analyzeResult.success) {
        updateProcessStep(processContainer, 'analyzing', 'failed', analyzeResult.message || t('ds_analyze_failed'));
        resetStartButton(startBtn, abandonBtn, t('ds_rescue_again'));
        return;
      }

      if (analyzeResult.official_agent_usage) {
        const usageInfo = analyzeResult.official_agent_usage;
        let usageText = '';
        if (usageInfo.free) {
          usageText = `${t('dst_use_official_free')}${usageInfo.remaining_free} ${t('dst_times')}`;
        } else {
          usageText = `${t('dst_use_official_cost')}${usageInfo.consumed_compute} ${t('dst_compute')}`;
        }
        addProcessStep(processContainer, 'usage', 'ℹ️ ' + usageText, '');
      }

      const sourceLabel = analyzeResult.source === 'knowledge_base'
        ? '✅ ' + t('ds_kb_reuse')
        : (analyzeResult.is_appeal ? '✅ ' + t('ds_regenerated') : '✅ ' + t('ds_generated'));
      updateProcessStep(processContainer, 'analyzing', 'success', sourceLabel);

      addProcessStep(processContainer, 'solution', t('ds_solution_label'), analyzeResult.solution);

      addProcessStep(processContainer, 'verifying', t('ds_verifying'));
      const verifyResult = await api.verifyYunchongTask(taskId);

      if (!verifyResult.success) {
        updateProcessStep(processContainer, 'verifying', 'failed', verifyResult.message || t('ds_verify_failed'));
        lastFailureReason = verifyResult.verification?.reason || verifyResult.message || '';

        if (verifyResult.comfort_reward) {
          const cr = verifyResult.comfort_reward;
          let rewardText = `${t('dst_sunlight_plus')}${cr.sunlight}`;
          if (cr.exp_small) rewardText += ` · ${t('dst_exp_small_plus')}${cr.exp_small}`;
          addProcessStep(processContainer, 'comfort', '💊 ' + t('ds_comfort'), rewardText);
        }

        const nextAttempts = (verifyResult.attempts || 0) + 1;
        if (nextAttempts >= 3) {
          addProcessStep(processContainer, 'hint', '💡 ' + t('ds_hint_label'), t('ds_hint_guarantee'));
        } else {
          addProcessStep(processContainer, 'hint', '💡 ' + t('ds_hint_label'), t('ds_hint_retry'));
        }

        resetStartButton(startBtn, abandonBtn, t('ds_rescue_again'));
        return;
      }

      updateProcessStep(processContainer, 'verifying', 'success', t('ds_verify_ok'));

      const reward = verifyResult.reward || {};
      const pet = verifyResult.pet || {};
      const guaranteedTag = verifyResult.is_guaranteed ? t('ds_guaranteed') : '';
      addProcessStep(processContainer, 'reward', '🎉 ' + t('ds_success') + guaranteedTag + '！', `
        ${t('ds_got_pet')}<strong>${pet.name || t('ds_unknown')}</strong>（${pet.rarity || ''}${t('ds_level_suffix')} · ${pet.camp || ''} · ${pet.element || ''}）
        <br>${t('ds_sunlight')}${reward.sunlight || 0}
        <br>${t('ds_exp_capsule')}${(reward.exp_small || 0) + (reward.exp_medium || 0) + (reward.exp_large || 0)}
        <br>${t('ds_universal_key')}${reward.universal_key || 0}
        ${verifyResult.kb_id ? '<br><span style="color:#34c759;">✅ ' + t('ds_saved_kb') + '</span>' : ''}
      `);

      startBtn.textContent = t('ds_done');
      startBtn.style.background = '#34c759';
      abandonBtn.style.display = 'none';

      if (typeof window.onboarding?.report === 'function') {
        window.onboarding.report('complete_rescue');
      }

    } catch (e) {
      addProcessStep(processContainer, 'error', '❌ ' + t('ds_error') + e.message, '');
      resetStartButton(startBtn, abandonBtn, t('ds_retry'));
    }
  };

  document.getElementById('rescue-abandon-btn').onclick = async () => {
    if (!confirm(t('discover_confirm_abandon'))) return;
    try {
      await api.abandonYunchongTask(taskId);
      alert(t('discover_abandoned'));
      openWisdomMap();
    } catch (e) {
      alert(t('discover_abandon_failed') + e.message);
    }
  };
}

function resetStartButton(btn, abandonBtn, text) {
  btn.disabled = false;
  btn.textContent = text;
  if (abandonBtn) abandonBtn.disabled = false;
  document.querySelectorAll('.agent-option-item').forEach(i => i.classList.remove('disabled'));
}

function addProcessStep(container, key, title, content) {
  const div = document.createElement('div');
  div.className = 'process-step';
  div.dataset.stepKey = key;
  div.innerHTML = `
    <div class="process-step-title">${title}</div>
    ${content ? `<div class="process-step-content">${content}</div>` : ''}
  `;
  container.appendChild(div);
  container.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function updateProcessStep(container, key, status, message) {
  const step = container.querySelector(`[data-step-key="${key}"]`);
  if (!step) return;
  step.classList.add(status);
  const titleEl = step.querySelector('.process-step-title');
  if (titleEl) {
    const icon = status === 'success' ? '✅ ' : status === 'failed' ? '❌ ' : '';
    titleEl.textContent = icon + titleEl.textContent.replace(/^[✅❌]\s*/, '');
  }
  if (message) {
    const contentEl = step.querySelector('.process-step-content');
    if (contentEl) {
      contentEl.textContent = message;
    } else {
      const div = document.createElement('div');
      div.className = 'process-step-content';
      div.textContent = message;
      step.appendChild(div);
    }
  }
}

// ==================== 云宠战役主页 ====================
function openYunchongCamp() {
  const html = `
    <div class="yunchong-hub">
      <div class="yunchong-banner">
        <div class="yunchong-title">${t('discover_yunchong_title')}</div>
        <div class="yunchong-subtitle">${t('yc_subtitle')}</div>
      </div>
      
      <div class="yunchong-nodes">
        <div class="yunchong-node" data-action="pets">
          <div class="yunchong-node-icon">🐾</div>
          <div class="yunchong-node-name">${t('yc_pets')}</div>
        </div>
        <div class="yunchong-node" data-action="base">
          <div class="yunchong-node-icon">🏠</div>
          <div class="yunchong-node-name">${t('yc_base')}</div>
        </div>
        <div class="yunchong-node" data-action="bag">
          <div class="yunchong-node-icon">🎒</div>
          <div class="yunchong-node-name">${t('yc_bag')}</div>
        </div>
        <div class="yunchong-node" data-action="battle">
          <div class="yunchong-node-icon">⚔️</div>
          <div class="yunchong-node-name">${t('yc_battle')}</div>
        </div>
      </div>
    </div>
  `;

  window.openSubpage(t('discover_yunchong_title'), html, {
    showMore: false,
    returnAction: () => openWisdomMap()
  });

  document.querySelectorAll('.yunchong-node').forEach(node => {
    node.onclick = () => {
      const action = node.dataset.action;
      const returnToYunchong = () => openYunchongCamp();

      if (action === 'pets') {
        if (typeof window.openPetList === 'function') window.openPetList(returnToYunchong);
      } else if (action === 'base') {
        if (typeof window.openBaseOverview === 'function') window.openBaseOverview(returnToYunchong);
      } else if (action === 'bag') {
        window.openSubpage(t('discover_bag'), `<div class="subpage-placeholder">${t('discover_bag_wip')}</div>`, { returnAction: returnToYunchong });
      } else if (action === 'battle') {
        window.openSubpage(t('discover_battle'), `<div class="subpage-placeholder">${t('discover_battle_wip')}</div>`, { returnAction: returnToYunchong });
      }
    };
  });
}

// ==================== 刷新倒计时 ====================
let refreshTimerInterval = null;

function startRefreshCountdown(seconds) {
  if (refreshTimerInterval) clearInterval(refreshTimerInterval);

  let remaining = seconds;
  updateRefreshTimer(remaining);

  refreshTimerInterval = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(refreshTimerInterval);
      refreshTimerInterval = null;
      openWisdomMap();
      return;
    }
    updateRefreshTimer(remaining);
  }, 1000);
}

function updateRefreshTimer(seconds) {
  const el = document.getElementById('map-refresh-timer');
  if (!el) return;
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  el.textContent = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

// ==================== AI圈 ====================
async function openAiCircle(title) {
  window.openSubpage(title, `<div class="subpage-placeholder">${t('loading')}</div>`);

  try {
    const data = await api.getAiCirclePosts();
    const posts = data.posts || [];
    let postsHtml;
    if (posts.length === 0) {
      postsHtml = `<div class="subpage-placeholder">${t('no_posts')}</div>`;
    } else {
      postsHtml = '<div class="ai-post-list">';
      posts.forEach(post => {
        const date = new Date(post.created_at).toLocaleString('zh-CN');
        postsHtml += `
          <div class="ai-post-item">
            <div class="ai-post-header">
              <span class="ai-post-agent">🤖 ${post.agent_id}</span>
              <span class="ai-post-owner">by ${post.owner_name}</span>
            </div>
            <div class="ai-post-content">${post.content}</div>
            <div class="ai-post-time">${date}</div>
          </div>
        `;
      });
      postsHtml += '</div>';
    }

    const contentHtml = `
      <div class="ai-publish-area">
        <textarea id="ai-post-input" class="ai-post-input" placeholder="${t('share_agent_moment')}"></textarea>
        <button id="ai-post-btn" class="save-btn">${t('publish')}</button>
      </div>
      ${postsHtml}
    `;
    document.getElementById('subpage-content').innerHTML = contentHtml;

    const publishBtn = document.getElementById('ai-post-btn');
    const postInput = document.getElementById('ai-post-input');
    if (publishBtn && postInput) {
      publishBtn.addEventListener('click', async () => {
        const content = postInput.value.trim();
        if (!content) { alert(t('please_input_all')); return; }
        try {
          await api.createAiCirclePost(content, 'daily');
          alert(t('publish_success'));
          postInput.value = '';
          openAiCircle(title);
        } catch (e) {
          alert(t('publish_failed') + ': ' + e.message);
        }
      });
    }
  } catch (e) {
    document.getElementById('subpage-content').innerHTML = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }
}

// ==================== 排行榜 ====================
async function openLeaderboard(title) {
  window.openSubpage(title, `<div class="subpage-placeholder">${t('loading')}</div>`);

  try {
    const data = await api.getLeaderboard();
    const users = data.leaderboard || [];
    let contentHtml;
    if (users.length === 0) {
      contentHtml = `<div class="subpage-placeholder">${t('no_data')}</div>`;
    } else {
      let listHtml = '<div class="me-menu">';
      users.forEach(user => {
        const medal = user.rank === 1 ? '🥇' : user.rank === 2 ? '🥈' : user.rank === 3 ? '🥉' : `${user.rank}.`;
        listHtml += `
          <div class="me-menu-item leaderboard-item">
            <span class="menu-icon">${medal}</span>
            <div class="leaderboard-avatar">${user.avatar}</div>
            <div class="menu-text">
              <div class="menu-title">${user.username}</div>
            </div>
          </div>
        `;
      });
      listHtml += '</div>';
      contentHtml = listHtml;
    }
    document.getElementById('subpage-content').innerHTML = contentHtml;
  } catch (e) {
    document.getElementById('subpage-content').innerHTML = `<div class="subpage-placeholder">${t('load_failed')}: ${e.message}</div>`;
  }
}

function getRarityColor(rarity) {
  const colors = {
    'C': '#888888',
    'B': '#4caf50',
    'A': '#2196f3',
    'S': '#9c27b0',
    'SR': '#ff9800',
    'SSR': '#ffd700'
  };
  return colors[rarity] || '#888';
}

window.openWisdomMap = openWisdomMap;