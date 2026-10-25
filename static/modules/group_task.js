import { apiFetch } from './utils.js';

let currentGroupId = null;
let currentGroupName = '群聊';

export function initGroupTask(groupId, groupName) {
  currentGroupId = groupId;
  currentGroupName = groupName || '群聊';
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
      taskPanel.innerHTML = '<div class="empty">请先进入一个群聊</div>';
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
  panel.innerHTML = '<div class="loading">加载任务中...</div>';
  try {
    const data = await apiFetch(`/group/${currentGroupId}/tasks`);
    renderTaskPanel(data.tasks || []);
  } catch (e) {
    panel.innerHTML = `<div class="error">加载失败：${e.message}</div>`;
  }
}

function renderTaskPanel(tasks) {
  const panel = document.getElementById('group-task-panel');
  if (!tasks.length) {
    panel.innerHTML = '<div class="empty">暂无任务</div>';
    return;
  }
  let html = '<div class="task-list">';
  tasks.forEach(task => {
    html += `
      <div class="task-card">
        <div class="task-title">${escapeHtml(task.description)}</div>
        <div class="task-meta">
          <span>来源：${escapeHtml(task.source_mode)}</span>
          <span>难度：${escapeHtml(task.difficulty)}</span>
          <span>状态：${escapeHtml(task.status)}</span>
        </div>
        <button class="btn-small" onclick="joinTask(${task.id})">一键参与</button>
      </div>
    `;
  });
  html += '</div>';
  panel.innerHTML = html;
}

async function joinTask(taskId) {
  try {
    await apiFetch(`/group/${currentGroupId}/task/${taskId}/join`, { method: 'POST' });
    alert('参与成功，系统已自动分配');
    loadTaskPanel();
  } catch (e) {
    alert('参与失败：' + e.message);
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