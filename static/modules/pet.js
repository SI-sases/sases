// static/modules/pet.js
import { api } from './api.js';

// ========== 宠物列表页 ==========
export async function openPetList(returnAction) {
  let petsHtml = '';
  try {
    const data = await api.getPetList();
    const pets = data.pets || [];
    if (pets.length === 0) {
      petsHtml = '<div class="subpage-placeholder">' + t('pet_empty') + '</div>';
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
    petsHtml = `<div class="subpage-placeholder">${t('pet_load_failed')}${e.message}</div>`;
  }

  const contentHtml = `<div id="pet-list-container">${petsHtml}</div>`;
  window.openSubpage(t('pet_my_pets'), contentHtml, {
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
    alert(t('pet_load_pets_failed') + e.message);
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
      <div style="font-size:13px;color:#888;margin-top:4px;">${t('pet_level')} ${pet.level} · ${t('pet_exp')} ${pet.exp}/${expNeeded}</div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item"><span class="menu-label">${t('pet_strength')}</span><span class="menu-value">${pet.strength}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('pet_hp')}</span><span class="menu-value">${pet.hp}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('pet_defense')}</span><span class="menu-value">${pet.defense}</span></div>
      <div class="me-menu-item"><span class="menu-label">${t('pet_skills')}</span><span class="menu-value">${pet.skill_slots} ${t('pet_count_unit')}</span></div>
    </div>
    <div class="me-menu">
      <div class="me-menu-item" id="pet-action-feed"><span class="menu-label">${t('pet_feed')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-evolve"><span class="menu-label">${t('pet_evolve')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-strengthen"><span class="menu-label">${t('pet_strengthen')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-awaken"><span class="menu-label">${t('pet_awaken')}</span><span class="menu-arrow">›</span></div>
      <div class="me-menu-item" id="pet-action-release"><span class="menu-label" style="color:#ff3b30;">${t('pet_release')}</span></div>
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
          alert(`${t('pet_feed_ok')} ${res.level}, ${t('pet_exp')} ${res.exp}`);
          // 上报新手引导动作：喂养宠物（Day 6）
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        } catch (e) { alert(t('pet_feed_failed') + e.message); }
      };
    }

    const evolveBtn = document.getElementById('pet-action-evolve');
    if (evolveBtn) {
      evolveBtn.onclick = async () => {
        if (!confirm(t('pet_evolve_confirm'))) return;
        try {
          const res = await api.evolvePet(petId);
          alert(res.message);
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        } catch (e) { alert(t('pet_evolve_failed') + e.message); }
      };
    }

    const strengthenBtn = document.getElementById('pet-action-strengthen');
    if (strengthenBtn) {
      strengthenBtn.onclick = () => {
        const attr = prompt(t('pet_strengthen_prompt'));
        let attribute = 'strength';
        if (attr === '2') attribute = 'hp';
        else if (attr === '3') attribute = 'defense';
        else if (attr !== '1') return;
        api.strengthenPet(petId, attribute).then(res => {
          alert(t('pet_strengthen_ok'));
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        }).catch(e => alert(t('pet_strengthen_failed') + e.message));
      };
    }

    const awakenBtn = document.getElementById('pet-action-awaken');
    if (awakenBtn) {
      awakenBtn.onclick = async () => {
        if (!confirm(t('pet_awaken_confirm'))) return;
        try {
          const res = await api.awakenPet(petId);
          alert(res.message);
          if (typeof window.onboarding?.report === 'function') {
            window.onboarding.report('feed_pet');
          }
          openPetDetail(petId, returnAction);
        } catch (e) { alert(t('pet_awaken_failed') + e.message); }
      };
    }

    const releaseBtn = document.getElementById('pet-action-release');
    if (releaseBtn) {
      releaseBtn.onclick = async () => {
        if (!confirm(t('pet_release_confirm'))) return;
        try {
          await api.releasePet(petId);
          alert(t('pet_released'));
          openPetList(returnAction);
        } catch (e) { alert(t('pet_release_failed') + e.message); }
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