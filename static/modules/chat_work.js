// static/modules/chat_work.js
import { appendWorkMessage } from './chat_ui.js';
import { t } from './i18n.js';

// ========== 风险提示 ==========
export function showWorkWarning(command, chatState, api) {
  const overlay = document.createElement('div');
  overlay.style.position = 'fixed';
  overlay.style.top = '0';
  overlay.style.left = '0';
  overlay.style.width = '100%';
  overlay.style.height = '100%';
  overlay.style.background = 'rgba(0,0,0,0.4)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.zIndex = '10000';

  const dialog = document.createElement('div');
  dialog.style.background = '#fff';
  dialog.style.borderRadius = '12px';
  dialog.style.padding = '20px';
  dialog.style.maxWidth = '90%';
  dialog.style.width = '360px';
  dialog.style.boxSizing = 'border-box';
  dialog.innerHTML = `
    <div style="font-size:16px; font-weight:600; margin-bottom:10px;">⚠️ ${t('cwk_risk_title')}</div>
    <div style="font-size:14px; color:#666; margin-bottom:16px;">${t('cwk_risk_desc_prefix')}<br><strong>${command}</strong><br><br>${t('cwk_risk_desc_suffix')}</div>
    <div style="font-size:14px; margin-bottom:16px;">
      <label><input type="checkbox" id="work-warning-disable-check"> ${t('cwk_dont_remind')}</label>
    </div>
    <div style="display:flex; gap:8px;">
      <button id="work-warning-cancel" style="flex:1; padding:10px; border:1px solid #ddd; border-radius:8px; background:#f5f5f5;">${t('cwk_cancel')}</button>
      <button id="work-warning-confirm" style="flex:1; padding:10px; border:none; border-radius:8px; background:#007aff; color:#fff;">${t('cwk_continue_exec')}</button>
    </div>
  `;

  overlay.appendChild(dialog);
  document.body.appendChild(overlay);

  const cleanup = () => {
    overlay.remove();
  };

  document.getElementById('work-warning-cancel').addEventListener('click', cleanup);
  document.getElementById('work-warning-confirm').addEventListener('click', () => {
    const disableCheck = document.getElementById('work-warning-disable-check');
    if (disableCheck.checked) {
      localStorage.setItem('sases_disable_work_warning', '1');
    }
    cleanup();
    sendWorkCommand(command, chatState, api);
  });
}

// ========== 执行指令 ==========
export async function sendWorkCommand(command, chatState, api) {
  const input = document.getElementById('chat-input');
  if (!command) return;

  appendWorkMessage('user', command, chatState.senderAgentId ? t('cw_agent') : t('cw_me'));
  input.value = '';
  if (typeof window.updateSendButtonVisibility === 'function') {
    window.updateSendButtonVisibility();
  }

  try {
    const data = await api.workExecute(chatState.conversationId, command, chatState.senderAgentId);
    if (data.conversation_id) {
      chatState.conversationId = data.conversation_id;
    }
    let resultText = data.output || t('cw_no_output');
    if (data.credit_deducted) {
      resultText += `\n\n⚠️ ${t('cw_credits_deducted')} ${t('cw_remaining')} ${data.credit_remaining ?? t('cw_unknown')}`;
    }
    appendWorkMessage('assistant', resultText, t('cw_cmd_exec'));

    // 上报新手引导动作：成功执行指令（Day 3）
    if (data.status !== 'blocked' && data.status !== 'error' && typeof window.onboarding?.report === 'function') {
      window.onboarding.report('execute_command');
    }
  } catch (err) {
    appendWorkMessage('assistant', `${t('cw_exec_failed')}${err.message}`, t('cw_cmd_exec'));
  }
}

// ========== 指挥官任务 ==========
export async function sendCommanderTask(taskText, chatState, api) {
  const input = document.getElementById('chat-input');
  if (!taskText) return;

  appendWorkMessage('user', taskText, chatState.senderAgentId ? t('cw_agent') : t('cw_me'));
  input.value = '';
  if (typeof window.updateSendButtonVisibility === 'function') {
    window.updateSendButtonVisibility();
  }

  appendCommanderHint(t('cw_commander_splitting'));

  try {
    const data = await api.commanderExecute(
      chatState.conversationId,
      taskText,
      chatState.senderAgentId
    );

    if (data.conversation_id) {
      chatState.conversationId = data.conversation_id;
    }

    if (!data.results || data.results.length === 0) {
      appendWorkMessage('assistant', data.message || t('cw_no_cmd'), t('cw_commander'));
      return;
    }

    data.results.forEach((r, idx) => {
      let stepText = `[${t('cwk_step')} ${idx + 1}] ${r.command}\n${t('cwk_status')}: ${r.status}\n${t('cwk_duration')}: ${r.duration_ms} ms`;
      if (r.status === 'success') {
        stepText += `\n${t('cwk_output')}:\n${r.output}`;
      } else if (r.status === 'blocked') {
        stepText += `\n⚠️ ${t('cw_blocked')}${r.output}`;
      } else {
        stepText += `\n${r.output}`;
      }
      appendWorkMessage('assistant', stepText, t('cw_commander'));
    });

    const summaryText = `✅ ${t('cw_task_done')} ${t('cw_executed')} ${data.commands_executed} ${t('cw_commands')}，${t('cw_success')} ${data.success_count} ${t('cw_items')}`;
    appendWorkMessage('assistant', summaryText, t('cw_commander'));

    // 上报新手引导动作（指挥官成功执行也算）
    if (data.success_count > 0 && typeof window.onboarding?.report === 'function') {
      window.onboarding.report('execute_command');
    }

  } catch (err) {
    appendWorkMessage('assistant', `${t('cw_commander_failed')}${err.message}`, t('cw_commander'));
  }
}

function appendCommanderHint(text) {
  const messages = document.getElementById('chat-messages');
  if (!messages) return;
  const div = document.createElement('div');
  div.style.textAlign = 'center';
  div.style.fontSize = '13px';
  div.style.color = '#888';
  div.style.margin = '8px 0';
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// ========== 首次进入引导卡片 ==========
export function showFreeModeGuide(container, isSases = false) {
  if (!container) return;
  const guide = document.createElement('div');
  guide.style.background = '#f7f9fc';
  guide.style.border = '1px solid #d0d7de';
  guide.style.borderRadius = '8px';
  guide.style.padding = '12px';
  guide.style.margin = '12px';
  guide.style.fontSize = '14px';
  guide.style.color = '#333';
  guide.innerHTML = `
    <div style="font-weight:600; margin-bottom:8px;">${t('work_guide_title')}</div>
    <div>· ${t('work_guide_direct')}</div>
    <div>· ${t('work_guide_0')}</div>
    <div>· ${t('work_guide_1')}</div>
    <div>· ${t('work_guide_2')}</div>
    <div>· ${t('work_guide_3')}</div>
    <div>· ${t('work_guide_4')}</div>

    ${isSases ? '<div>· ' + t('work_guide_kb') + '</div>' : ''}
    <div>· ${t('work_guide_switch')}</div>
    <div style="margin-top:8px; text-align:right;">
      <button id="dismiss-free-mode-guide" style="background:none; border:none; color:#007aff; cursor:pointer;">${t('work_guide_dismiss')}</button>
    </div>
  `;
  container.appendChild(guide);
  document.getElementById('dismiss-free-mode-guide').addEventListener('click', () => {
    localStorage.setItem('sases_free_mode_guide_dismissed', '1');
    guide.remove();
  });
}