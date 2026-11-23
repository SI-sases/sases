// static/modules/chat_draft.js
// 草稿任务编辑器 + 蜂群操作按钮

import { api } from './api.js'; import { t } from './i18n.js';


export function showProposedRunCard(runId) {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  const wrap = document.createElement('div');
  wrap.style.margin = '8px 12px';
  wrap.style.padding = '12px';
  wrap.style.background = '#fff9e6';
  wrap.style.border = '1px solid #ffcc00';
  wrap.style.borderRadius = '8px';
  wrap.id = 'proposed-run-' + runId;
  const title = document.createElement('div');
  title.textContent = '⚡ ' + t('cd_proposal');
  title.style.fontWeight = '600';
  title.style.marginBottom = '8px';
  wrap.appendChild(title);
  const btnGroup = document.createElement('div');
  btnGroup.style.display = 'flex';
  btnGroup.style.gap = '8px';
  btnGroup.style.justifyContent = 'flex-end';
  const rejectBtn = document.createElement('button');
  rejectBtn.textContent = '✕ ' + t('cd_cancel');
  rejectBtn.style.padding = '6px 16px';
  rejectBtn.style.fontSize = '13px';
  rejectBtn.style.border = '1px solid #ccc';
  rejectBtn.style.background = '#fff';
  rejectBtn.style.borderRadius = '4px';
  rejectBtn.style.cursor = 'pointer';
  rejectBtn.onclick = async () => {
    try {
      await api.rejectRun(runId);
      btnGroup.remove();
      title.textContent = t('cd_rejected_notified');
      wrap.style.borderColor = '#ddd';
      wrap.style.background = '#f5f5f5';
    } catch (e) {
      alert(t('cd_cancel_failed') + (e.message || t('cd_unknown_error')));
    }
  };
  const confirmBtn = document.createElement('button');
  confirmBtn.textContent = t('cd_execute');
  confirmBtn.style.padding = '6px 16px';
  confirmBtn.style.fontSize = '13px';
  confirmBtn.style.border = 'none';
  confirmBtn.style.color = '#fff';
  confirmBtn.style.background = '#007aff';
  confirmBtn.style.borderRadius = '4px';
  confirmBtn.style.cursor = 'pointer';
  confirmBtn.onclick = async () => {
    confirmBtn.disabled = true;
    confirmBtn.textContent = t('cd_submitted');
    try {
      await api.confirmRun(runId);
      btnGroup.remove();
      title.textContent = '✅ ' + t('cd_confirmed');
    } catch (e) {
      confirmBtn.disabled = false;
      confirmBtn.textContent = '▶ ' + t('cd_execute');
      alert(t('cd_confirm_failed') + '：' + (e.message || t('cd_unknown_error')));
    }
  };
  btnGroup.appendChild(rejectBtn);
  btnGroup.appendChild(confirmBtn);
  wrap.appendChild(btnGroup);
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

export function showTaskDraftEditor(taskId, steps) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const wrap = document.createElement('div');
  wrap.style.margin = '8px 12px';
  wrap.style.padding = '12px';
  wrap.style.background = '#f8f9fa';
  wrap.style.borderRadius = '8px';
  wrap.style.border = '1px solid #e0e0e0';
  wrap.id = `task-draft-${taskId}`;

  const title = document.createElement('div');
  title.textContent = '📝 ' + t('cd_draft_title');
  title.style.fontWeight = '600';
  title.style.marginBottom = '10px';
  title.style.fontSize = '14px';
  wrap.appendChild(title);

  const list = document.createElement('div');
  list.style.display = 'flex';
  list.style.flexDirection = 'column';
  list.style.gap = '8px';
  list.style.marginBottom = '10px';

  let currentSteps = steps.map(s => ({
    ...s,
    step: s.step,
    description: s.description || '',
    command: s.command || ''
  }));

  function renderList() {
    list.innerHTML = '';
    currentSteps.forEach((s, idx) => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.flexDirection = 'column';
      row.style.gap = '4px';
      row.style.padding = '6px';
      row.style.background = '#fff';
      row.style.borderRadius = '4px';
      row.style.border = '1px solid #ddd';

      const topLine = document.createElement('div');
      topLine.style.display = 'flex';
      topLine.style.alignItems = 'center';
      topLine.style.gap = '6px';

      const numLabel = document.createElement('span');
      numLabel.textContent = `步骤 ${idx + 1}`;
      numLabel.style.fontSize = '12px';
      numLabel.style.color = '#666';
      numLabel.style.minWidth = '50px';
      topLine.appendChild(numLabel);

      const delBtn = document.createElement('button');
      delBtn.textContent = t('cd_delete');
      delBtn.style.marginLeft = 'auto';
      delBtn.style.fontSize = '12px';
      delBtn.style.border = '1px solid #ff3b30';
      delBtn.style.color = '#ff3b30';
      delBtn.style.background = '#fff';
      delBtn.style.borderRadius = '4px';
      delBtn.style.padding = '2px 8px';
      delBtn.style.cursor = 'pointer';
      delBtn.onclick = () => {
        currentSteps.splice(idx, 1);
        renderList();
      };
      topLine.appendChild(delBtn);
      row.appendChild(topLine);

      const descInput = document.createElement('input');
      descInput.type = 'text';
      descInput.value = s.description || '';
      descInput.placeholder = t('cd_desc_ph');
      descInput.style.fontSize = '12px';
      descInput.style.padding = '4px 8px';
      descInput.style.border = '1px solid #ddd';
      descInput.style.borderRadius = '4px';
      descInput.style.outline = 'none';
      descInput.oninput = (e) => { currentSteps[idx].description = e.target.value; };
      row.appendChild(descInput);

      const cmdInput = document.createElement('input');
      cmdInput.type = 'text';
      cmdInput.value = s.command || '';
      cmdInput.placeholder = t('cd_cmd_ph');
      cmdInput.style.fontSize = '13px';
      cmdInput.style.padding = '4px 8px';
      cmdInput.style.border = '1px solid #ddd';
      cmdInput.style.borderRadius = '4px';
      cmdInput.style.fontFamily = 'Consolas, Monaco, monospace';
      cmdInput.style.outline = 'none';
      cmdInput.oninput = (e) => { currentSteps[idx].command = e.target.value; };
      row.appendChild(cmdInput);

      list.appendChild(row);
    });
  }

  renderList();
  wrap.appendChild(list);

  const addBtn = document.createElement('button');
  addBtn.textContent = '+ ' + t('cd_add_step');
  addBtn.style.fontSize = '12px';
  addBtn.style.padding = '4px 12px';
  addBtn.style.border = '1px dashed #999';
  addBtn.style.color = '#666';
  addBtn.style.background = '#fff';
  addBtn.style.borderRadius = '4px';
  addBtn.style.cursor = 'pointer';
  addBtn.style.marginBottom = '12px';
  addBtn.onclick = () => {
    currentSteps.push({ step: currentSteps.length + 1, description: '', command: '', type: 'command' });
    renderList();
  };
  wrap.appendChild(addBtn);

  const btnGroup = document.createElement('div');
  btnGroup.style.display = 'flex';
  btnGroup.style.gap = '8px';
  btnGroup.style.justifyContent = 'flex-end';

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = t('cd_cancel_btn');
  cancelBtn.style.padding = '6px 16px';
  cancelBtn.style.fontSize = '13px';
  cancelBtn.style.border = '1px solid #ccc';
  cancelBtn.style.background = '#fff';
  cancelBtn.style.borderRadius = '4px';
  cancelBtn.style.cursor = 'pointer';
  cancelBtn.onclick = async () => {
    cancelBtn.disabled = true;
    try {
      const token = localStorage.getItem('sases_token');
      await fetch('/swarm/cancel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ task_id: taskId })
      });
    } catch (e) {
      console.error('取消失败', e);
    }
    wrap.remove();
  };
  btnGroup.appendChild(cancelBtn);

  const confirmBtn = document.createElement('button');
  confirmBtn.textContent = '✓ ' + t('cd_confirm_exec');
  confirmBtn.style.padding = '6px 16px';
  confirmBtn.style.fontSize = '13px';
  confirmBtn.style.border = 'none';
  confirmBtn.style.color = '#fff';
  confirmBtn.style.background = '#007aff';
  confirmBtn.style.borderRadius = '4px';
  confirmBtn.style.cursor = 'pointer';
  confirmBtn.onclick = async () => {
    confirmBtn.disabled = true;
    confirmBtn.textContent = t('cd_submitted');
    try {
      const token = localStorage.getItem('sases_token');
      const resp = await fetch('/swarm/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ task_id: taskId, edited_steps: currentSteps })
      });
      const data = await resp.json();
      if (data.status === 'confirmed') {
        wrap.remove();
      } else {
        confirmBtn.disabled = false;
        confirmBtn.textContent = '✓ ' + t('cd_confirm_exec');
        alert(t('cd_confirm_failed') + (data.message || t('cd_unknown_error')));
      }
    } catch (e) {
      confirmBtn.disabled = false;
      confirmBtn.textContent = '✓ ' + t('cd_confirm_exec');
      alert(t('cd_request_failed') + e.message);
    }
  };
  btnGroup.appendChild(confirmBtn);

  wrap.appendChild(btnGroup);

  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

// ========== 蜂群任务操作按钮（取消 + 误判反馈） ==========
export function showSwarmActionButtons(taskId, originalInput, swarmStatus) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  const wrap = document.createElement('div');
  wrap.style.display = 'flex';
  wrap.style.justifyContent = 'center';
  wrap.style.gap = '10px';
  wrap.style.margin = '6px 12px';
  wrap.id = `swarm-actions-${taskId}`;

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = '⏹ ' + t('cd_cancel_exec');
  cancelBtn.style.padding = '6px 16px';
  cancelBtn.style.fontSize = '13px';
  cancelBtn.style.border = '1px solid #ff3b30';
  cancelBtn.style.color = '#ff3b30';
  cancelBtn.style.background = '#fff';
  cancelBtn.style.borderRadius = '16px';
  cancelBtn.style.cursor = 'pointer';
  cancelBtn.style.transition = 'all 0.2s';
  cancelBtn.onmouseenter = () => { cancelBtn.style.background = '#fff5f5'; };
  cancelBtn.onmouseleave = () => { cancelBtn.style.background = '#fff'; };

  cancelBtn.onclick = async () => {
    cancelBtn.disabled = true;
    cancelBtn.textContent = t('cd_cancelled');
    cancelBtn.style.color = '#999';
    cancelBtn.style.borderColor = '#999';
    cancelBtn.style.cursor = 'default';
    try {
      const token = localStorage.getItem('sases_token');
      await fetch('/swarm/cancel', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ task_id: taskId })
      });
    } catch (e) {
      console.error('取消失败', e);
    }
    setTimeout(() => {
      if (wrap.parentNode) wrap.remove();
    }, 1500);
  };

  const feedbackBtn = document.createElement('button');
  feedbackBtn.textContent = '❌ ' + t('cd_not_task');
  feedbackBtn.style.padding = '6px 16px';
  feedbackBtn.style.fontSize = '13px';
  feedbackBtn.style.border = '1px solid #888';
  feedbackBtn.style.color = '#666';
  feedbackBtn.style.background = '#fff';
  feedbackBtn.style.borderRadius = '16px';
  feedbackBtn.style.cursor = 'pointer';
  feedbackBtn.style.transition = 'all 0.2s';
  feedbackBtn.onmouseenter = () => { feedbackBtn.style.background = '#f5f5f5'; };
  feedbackBtn.onmouseleave = () => { feedbackBtn.style.background = '#fff'; };

  feedbackBtn.onclick = async () => {
    feedbackBtn.disabled = true;
    feedbackBtn.textContent = t('cd_recorded');
    feedbackBtn.style.color = '#999';
    feedbackBtn.style.borderColor = '#ccc';
    feedbackBtn.style.cursor = 'default';

    if (cancelBtn.parentNode) {
      cancelBtn.disabled = true;
      cancelBtn.textContent = t('cd_cancelled');
      cancelBtn.style.color = '#ccc';
      cancelBtn.style.borderColor = '#ccc';
      cancelBtn.style.cursor = 'default';
    }

    try {
      const token = localStorage.getItem('sases_token');
      await fetch('/swarm/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          task_id: taskId,
          original_input: originalInput,
          feedback_type: 'false_positive'
        })
      });
    } catch (e) {
      console.error('反馈失败', e);
    }
    setTimeout(() => {
      if (wrap.parentNode) wrap.remove();
    }, 1500);
  };

  if (swarmStatus === 'planned') {
    wrap.appendChild(cancelBtn);
  }
  wrap.appendChild(feedbackBtn);

  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;

  setTimeout(() => {
    if (wrap.parentNode) wrap.remove();
  }, 10000);
}

