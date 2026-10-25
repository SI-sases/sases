// static/modules/base.js
import { api } from './api.js';

// ========== 基地总览页 ==========
export async function openBaseOverview(returnAction) {
  let overviewHtml = '';
  try {
    const data = await api.getBaseOverview();
    const facilities = data.facilities || [];
    const resources = data.resources || {};

    let resourcesHtml = '<div class="base-resources-bar">';
    const resourceIcons = {
      '阳光': '☀️',
      '能量石': '🔋',
      '进化石': '💎',
      '强化石': '⚒️',
      '晶石': '🔮',
      '万能钥匙': '🔑',
      '觉醒之心': '❤️'
    };
    for (const [key, value] of Object.entries(resources)) {
      const icon = resourceIcons[key] || '📦';
      resourcesHtml += `
        <div class="resource-item">
          <span class="resource-icon">${icon}</span>
          <span class="resource-name">${key}</span>
          <span class="resource-amount">${value}</span>
        </div>
      `;
    }
    resourcesHtml += '</div>';

    let facilitiesHtml = '<div class="base-facilities">';
    facilities.forEach(f => {
      const facilityIcon = getFacilityIcon(f.facility_type);
      const rateText = f.output_per_hour > 0 ? `${f.output_per_hour}/小时` : '未建造';
      const captainText = f.captain_pet_id ? '已任命队长' : '无队长';
      const memberCount = (f.member_pet_ids || []).length;

      facilitiesHtml += `
        <div class="facility-card" data-facility-type="${f.facility_type}">
          <div class="facility-icon">${facilityIcon}</div>
          <div class="facility-info">
            <div class="facility-name">${f.facility_type} <span class="facility-level">Lv.${f.level}</span></div>
            <div class="facility-output">产出：${f.output_resource} ${rateText}</div>
            <div class="facility-crew">${captainText} · 队员 ${memberCount}/3</div>
          </div>
          <div class="facility-actions">
            <button class="facility-btn collect-btn" data-facility-type="${f.facility_type}">收取</button>
            <button class="facility-btn upgrade-btn" data-facility-type="${f.facility_type}">升级</button>
          </div>
        </div>
      `;
    });
    facilitiesHtml += '</div>';

    overviewHtml = resourcesHtml + facilitiesHtml;
  } catch (e) {
    overviewHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `<div id="base-overview-container">${overviewHtml}</div>`;
  window.openSubpage('我的基地', contentHtml, {
    showMore: false,
    returnAction: returnAction
  });

  function bindFacilities() {
    document.querySelectorAll('.facility-card').forEach(card => {
      card.onclick = (e) => {
        if (e.target.closest('.facility-btn')) return;
        const ftype = card.dataset.facilityType;
        openFacilityDetail(ftype, () => openBaseOverview(returnAction));
      };
    });

    document.querySelectorAll('.collect-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const ftype = btn.dataset.facilityType;
        try {
          const res = await api.collectBaseOutput(ftype);
          alert(`收取成功：${res.resource} × ${res.amount}`);
          openBaseOverview(returnAction);
        } catch (err) {
          alert('收取失败：' + err.message);
        }
      };
    });

    document.querySelectorAll('.upgrade-btn').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const ftype = btn.dataset.facilityType;
        try {
          const costInfo = await api.getBaseUpgradeCost(ftype);
          if (!costInfo.success) {
            alert(costInfo.message);
            return;
          }
          if (!confirm(`升级消耗：${costInfo.cost_resource} × ${costInfo.cost_amount}\n是否继续？`)) return;
          const res = await api.upgradeBaseFacility(ftype);
          alert(res.message);
          // 上报新手引导动作：升级设施（Day 7）
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('upgrade_facility');
          }
          openBaseOverview(returnAction);
        } catch (err) {
          alert('升级失败：' + err.message);
        }
      };
    });
  }

  setTimeout(bindFacilities, 100);
}

// ========== 设施详情页 ==========
export async function openFacilityDetail(facilityType, returnAction) {
  let facility = null;
  let petsData = null;
  try {
    facility = await api.getBaseFacility(facilityType);
    const petsResp = await api.getPetList();
    petsData = petsResp.pets || [];
  } catch (e) {
    alert('加载失败：' + e.message);
    return;
  }

  const icon = getFacilityIcon(facilityType);
  const captainId = facility.captain_pet_id;
  const members = facility.member_pet_ids || [];

  let petOptionsHtml = '';
  petsData.forEach(pet => {
    const emoji = getPetEmoji(pet.camp, pet.rarity);
    const isCaptain = pet.id === captainId;
    const isMember = members.includes(pet.id);
    let statusTag = '';
    if (isCaptain) statusTag = ' <span style="color:#ff9500;">[队长]</span>';
    else if (isMember) statusTag = ' <span style="color:#34c759;">[队员]</span>';

    petOptionsHtml += `
      <div class="pet-option-item" data-pet-id="${pet.id}">
        <span class="pet-option-emoji">${emoji}</span>
        <span class="pet-option-name">${pet.pet_name} (${pet.rarity})${statusTag}</span>
      </div>
    `;
  });

  const contentHtml = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:64px;">${icon}</div>
      <div style="font-size:20px;font-weight:600;margin-top:8px;">${facilityType}</div>
      <div style="font-size:14px;color:#888;">等级 ${facility.level} · 产出 ${facility.output_resource || '无'}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">当前产出</span><span class="menu-value">${getFacilityRate(facility)}/小时</span></div>
      <div class="me-menu-item"><span class="menu-label">队长</span><span class="menu-value">${captainId ? '已任命' : '未任命'}</span></div>
      <div class="me-menu-item"><span class="menu-label">队员</span><span class="menu-value">${members.length}/3</span></div>
    </div>
    <div class="section-title">宠物任职</div>
    <div id="facility-pet-list" class="me-menu">
      ${petOptionsHtml || '<div class="subpage-placeholder">暂无宠物</div>'}
    </div>
  `;
  window.openSubpage(facilityType, contentHtml, {
    showMore: false,
    returnAction: returnAction
  });

  function bindPetOptions() {
    document.querySelectorAll('.pet-option-item').forEach(item => {
      item.onclick = () => {
        const petId = parseInt(item.dataset.petId);
        let action = prompt(
          `选择操作：\n1. 任命为队长\n2. 添加为队员\n3. 移除\n0. 取消`
        );
        if (action === '1') {
          api.assignBaseCaptain(facilityType, petId).then(res => {
            if (res.success) {
              alert('任命成功');
              openFacilityDetail(facilityType, returnAction);
            } else {
              alert(res.message);
            }
          }).catch(e => alert('任命失败：' + e.message));
        } else if (action === '2') {
          api.assignBaseMember(facilityType, petId).then(res => {
            if (res.success) {
              alert('添加成功');
              openFacilityDetail(facilityType, returnAction);
            } else {
              alert(res.message);
            }
          }).catch(e => alert('添加失败：' + e.message));
        } else if (action === '3') {
          api.removeBaseMember(facilityType, petId).then(res => {
            if (res.success) {
              alert('移除成功');
              openFacilityDetail(facilityType, returnAction);
            } else {
              alert(res.message);
            }
          }).catch(e => alert('移除失败：' + e.message));
        }
      };
    });
  }

  setTimeout(bindPetOptions, 100);
}

// ========== 工具函数 ==========
function getFacilityIcon(facilityType) {
  const icons = {
    '补给站': '🔋',
    '采集站': '☀️',
    '进化站': '💎',
    '强化站': '⚒️',
    '结晶站': '🔮',
    '通讯站': '📡'
  };
  return icons[facilityType] || '🏭';
}

function getFacilityRate(facility) {
  if (!facility || facility.level === 0) return '0';
  const base = facility.output_per_hour || 0;
  return base.toFixed(2);
}

function getPetEmoji(camp, rarity) {
  const campEmoji = {
    '植物': '🌱',
    '海洋': '🐟',
    '动物': '🐱',
    '菌群': '🍄',
    '飞行': '🦅',
    '碳基': '🔥',
    '硅基': '💎'
  };
  const rarityUpgrade = {
    'C': '',
    'B': '',
    'A': '✨',
    'S': '🌟',
    'SR': '💫',
    'SSR': '👑'
  };
  return (campEmoji[camp] || '❓') + (rarityUpgrade[rarity] || '');
}

window.openBaseOverview = openBaseOverview;
window.openFacilityDetail = openFacilityDetail;