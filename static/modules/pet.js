// static/modules/pet.js
import { api } from './api.js';

// ========== 宠物列表页 ==========
export async function openPetList(returnAction) {
  let petsHtml = '';
  try {
    const data = await api.getPetList();
    const pets = data.pets || [];
    if (pets.length === 0) {
      petsHtml = '<div class="subpage-placeholder">暂无宠物，去完成解救任务获得宠物吧</div>';
    } else {
      petsHtml = '<div class="pet-grid">';
      pets.forEach(pet => {
        const emoji = getPetEmoji(pet.camp, pet.rarity);
        const borderColor = getRarityColor(pet.rarity);
        petsHtml += `
          <div class="pet-card" data-pet-id="${pet.id}" style="border-color:${borderColor};">
            <div class="pet-emoji">${emoji}</div>
            <div class="pet-name">${pet.pet_name}</div>
            <div class="pet-rarity" style="color:${borderColor};">${pet.rarity}</div>
            <div class="pet-level">Lv.${pet.level}</div>
          </div>
        `;
      });
      petsHtml += '</div>';
    }
  } catch (e) {
    petsHtml = `<div class="subpage-placeholder">加载失败：${e.message}</div>`;
  }

  const contentHtml = `<div id="pet-list-container">${petsHtml}</div>`;
  window.openSubpage('我的宠物', contentHtml, {
    showMore: false,
    returnAction: returnAction
  });

  function bindPetCards() {
    document.querySelectorAll('.pet-card').forEach(card => {
      card.onclick = () => {
        const petId = card.dataset.petId;
        openPetDetail(petId, () => openPetList(returnAction));
      };
    });
  }

  setTimeout(bindPetCards, 100);
}

// ========== 宠物详情页 ==========
export async function openPetDetail(petId, returnAction) {
  let pet = null;
  try {
    pet = await api.getPet(petId);
  } catch (e) {
    alert('加载宠物失败：' + e.message);
    return;
  }

  const emoji = getPetEmoji(pet.camp, pet.rarity);
  const borderColor = getRarityColor(pet.rarity);
  const expNeeded = pet.level * 20;

  const contentHtml = `
    <div style="text-align:center;padding:20px;">
      <div style="font-size:72px;">${emoji}</div>
      <div style="font-size:20px;font-weight:600;margin-top:8px;">${pet.pet_name}</div>
      <div style="font-size:14px;color:${borderColor};margin-top:4px;">${pet.rarity} · ${pet.camp} · ${pet.element}</div>
      <div style="font-size:13px;color:#888;margin-top:4px;">等级 ${pet.level} · 经验 ${pet.exp}/${expNeeded}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">力量</span><span class="menu-value">${pet.strength}</span></div>
      <div class="me-menu-item"><span class="menu-label">生命</span><span class="menu-value">${pet.hp}</span></div>
      <div class="me-menu-item"><span class="menu-label">防御</span><span class="menu-value">${pet.defense}</span></div>
      <div class="me-menu-item"><span class="menu-label">技能栏</span><span class="menu-value">${pet.skill_slots} 个</span></div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="pet-action-feed"><span class="menu-label">喂养（+10经验）</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-evolve"><span class="menu-label">进化</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-strengthen"><span class="menu-label">强化属性</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-awaken"><span class="menu-label">觉醒</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-release"><span class="menu-label" style="color:#ff3b30;">放生</span></div>
    </div>
  `;
  window.openSubpage(pet.pet_name, contentHtml, {
    showMore: false,
    returnAction: returnAction
  });

  function bindActions() {
    const feedBtn = document.getElementById('pet-action-feed');
    if (feedBtn) {
      feedBtn.onclick = async () => {
        try {
          const res = await api.feedPet(petId, 10);
          alert(`喂养成功！当前等级 ${res.level}，经验 ${res.exp}`);
          // 上报新手引导动作：喂养宠物（Day 6）
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        } catch (e) { alert('喂养失败：' + e.message); }
      };
    }

    const evolveBtn = document.getElementById('pet-action-evolve');
    if (evolveBtn) {
      evolveBtn.onclick = async () => {
        if (!confirm('进化将消耗进化石，是否继续？')) return;
        try {
          const res = await api.evolvePet(petId);
          alert(res.message);
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        } catch (e) { alert('进化失败：' + e.message); }
      };
    }

    const strengthenBtn = document.getElementById('pet-action-strengthen');
    if (strengthenBtn) {
      strengthenBtn.onclick = () => {
        const attr = prompt('选择强化属性：\n1. 力量\n2. 生命\n3. 防御\n\n请输入 1/2/3');
        let attribute = 'strength';
        if (attr === '2') attribute = 'hp';
        else if (attr === '3') attribute = 'defense';
        else if (attr !== '1') return;
        api.strengthenPet(petId, attribute).then(res => {
          alert('强化成功！');
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        }).catch(e => alert('强化失败：' + e.message));
      };
    }

    const awakenBtn = document.getElementById('pet-action-awaken');
    if (awakenBtn) {
      awakenBtn.onclick = async () => {
        if (!confirm('觉醒消耗觉醒之心，是否继续？')) return;
        try {
          const res = await api.awakenPet(petId);
          alert(res.message);
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        } catch (e) { alert('觉醒失败：' + e.message); }
      };
    }

    const releaseBtn = document.getElementById('pet-action-release');
    if (releaseBtn) {
      releaseBtn.onclick = async () => {
        if (!confirm('确定放生这只宠物吗？此操作不可恢复。')) return;
        try {
          await api.releasePet(petId);
          alert('已放生');
          openPetList(returnAction);
        } catch (e) { alert('放生失败：' + e.message); }
      };
    }
  }

  setTimeout(bindActions, 100);
}

// ========== 工具函数 ==========
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

window.openPetList = openPetList;
window.openPetDetail = openPetDetail;