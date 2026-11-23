import { apiFetch } from './utils.js';
import { t } from './i18n.js';

let currentGroupId = null;
let currentGroupName = t('msg_group');

export function initGroupTask(groupId, groupName) {
  currentGroupId = groupId;
  currentGroupName = groupName || t('msg_group');
  document.getElementById('top-title').textContent = currentGroupName;
  bindModeButtons();
  switchMode('chat');
}

export function switchMode(mode) {
  const messages = document.getElementById('chat-messages');
  const inputArea = document.getElementById('chat-input-area');
  const taskPanel = document.getElementById('group-task-panel');

  if (mode === 'chat') {
    messages.style.display = 'block';
    inputArea.style.display = 'flex';
    taskPanel.style.display = 'none';
  } else if (mode === 'task') {
    messages.style.display = 'none';
    inputArea.style.display = 'none';
    taskPanel.style.display = 'block';
    if (currentGroupId) {
      loadTaskPanel();
    } else {
      taskPanel.innerHTML = '<div class="empty">' + t('gt2_enter_group') + '</div>';
    }
  }

  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.dataset.mode === mode) btn.classList.add('active');
  });
}

function bindModeButtons() {
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.onclick = () => {
      const mode = btn.dataset.mode;
      switchMode(mode);
    };
  });
}

async function loadTaskPanel() {
  const panel = document.getElementById('group-task-panel');
  panel.innerHTML = '<div class="loading">' + t('gt2_loading') + '</div>';
  try {
    const data = await apiFetch(`/group/${currentGroupId}/tasks`);
    renderTaskPanel(data.tasks || []);
  } catch (e) {
    panel.innerHTML = `<div class="error">${t('gt2_load_failed')}${e.message}</div>`;
  }
}

function renderTaskPanel(tasks) {
  const panel = document.getElementById('group-task-panel');
  if (!tasks.length) {
    panel.innerHTML = '<div class="empty">' + t('gt2_empty') + '</div>';
    return;
  }
  let html = '<div class="task-list">';
  tasks.forEach(task => {
    html += `
      <div class="task-card">
        <div class="task-title">${escapeHtml(task.description)}</div>
        <div class="task-meta">
          <span>${t('gt2_source')}${escapeHtml(task.source_mode)}</span>
          <span>${t('gt2_difficulty')}${escapeHtml(task.difficulty)}</span>
          <span>${t('gt2_status')}${escapeHtml(task.status)}</span>
        </div>
        <button class="btn-small" onclick="joinTask(${task.id})">${t('gt2_join')}</button>
      </div>
    `;
  });
  html += '</div>';
  panel.innerHTML = html;
}

async function joinTask(taskId) {
  try {
    await apiFetch(`/group/${currentGroupId}/task/${taskId}/join`, { method: 'POST' });
    alert(t('gt2_join_ok'));
    loadTaskPanel();
  } catch (e) {
    alert(t('gt2_join_failed') + e.message);
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 暴露给全局使用
window.switchMode = switchMode;
window.joinTask = joinTask;
window.initGroupTask = initGroupTask;