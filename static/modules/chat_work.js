// static/modules/chat_work.js
import { appendWorkMessage } from './chat_ui.js';

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
    <div style="font-size:16px; font-weight:600; margin-bottom:10px;">⚠️ 指令执行风险提示</div>
    <div style="font-size:14px; color:#666; margin-bottom:16px;">即将在本地执行命令：<br><strong>${command}</strong><br><br>请确认该命令来自可信来源。危险命令已被白名单拦截，但请谨慎使用。</div>
    <div style="font-size:14px; margin-bottom:16px;">
      <label><input type="checkbox" id="work-warning-disable-check"> 今后不再提醒</label>
    </div>
    <div style="display:flex; gap:8px;">
      <button id="work-warning-cancel" style="flex:1; padding:10px; border:1px solid #ddd; border-radius:8px; background:#f5f5f5;">取消</button>
      <button id="work-warning-confirm" style="flex:1; padding:10px; border:none; border-radius:8px; background:#007aff; color:#fff;">继续执行</button>
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

  appendWorkMessage('user', command, chatState.senderAgentId ? '智能体' : '我');
  input.value = '';
  if (typeof window.updateSendButtonVisibility === 'function') {
    window.updateSendButtonVisibility();
  }

  try {
    const data = await api.workExecute(chatState.conversationId, command, chatState.senderAgentId);
    if (data.conversation_id) {
      chatState.conversationId = data.conversation_id;
    }
    let resultText = data.output || '(无输出)';
    if (data.credit_deducted) {
      resultText += `\n\n⚠️ 已扣除 2 积分，剩余 ${data.credit_remaining ?? '未知'}`;
    }
    appendWorkMessage('assistant', resultText, '指令执行');

    // 上报新手引导动作：成功执行指令（Day 3）
    if (data.status !== 'blocked' && data.status !== 'error' && typeof window.onboarding?.report === 'function') {
      window.onboarding.report('execute_command');
    }
  } catch (err) {
    appendWorkMessage('assistant', `执行失败：${err.message}`, '指令执行');
  }
}

// ========== 指挥官任务 ==========
export async function sendCommanderTask(taskText, chatState, api) {
  const input = document.getElementById('chat-input');
  if (!taskText) return;

  appendWorkMessage('user', taskText, chatState.senderAgentId ? '智能体' : '我');
  input.value = '';
  if (typeof window.updateSendButtonVisibility === 'function') {
    window.updateSendButtonVisibility();
  }

  appendCommanderHint('指挥官正在拆解任务...');

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
      appendWorkMessage('assistant', data.message || '未能生成可执行命令', '指挥官');
      return;
    }

    data.results.forEach((r, idx) => {
      let stepText = `[步骤 ${idx + 1}] ${r.command}\n状态: ${r.status}\n耗时: ${r.duration_ms} ms`;
      if (r.status === 'success') {
        stepText += `\n输出:\n${r.output}`;
      } else if (r.status === 'blocked') {
        stepText += `\n⚠️ 已被拦截：${r.output}`;
      } else {
        stepText += `\n${r.output}`;
      }
      appendWorkMessage('assistant', stepText, '指挥官');
    });

    const summaryText = `✅ 任务完成，共执行 ${data.commands_executed} 条命令，成功 ${data.success_count} 条`;
    appendWorkMessage('assistant', summaryText, '指挥官');

    // 上报新手引导动作（指挥官成功执行也算）
    if (data.success_count > 0 && typeof window.onboarding?.report === 'function') {
      window.onboarding.report('execute_command');
    }

  } catch (err) {
    appendWorkMessage('assistant', `指挥官任务失败：${err.message}`, '指挥官');
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
    <div style="font-weight:600; margin-bottom:8px;">💡 使用提示</div>
    <div>· 直接输入文字与我对话</div>
    <div>· #0：清除会话锁，例 #0：清锁</div>
            <div>· #1：跑一条命令，例 #1：看看 core 目录有什么</div>
    <div>· #2：让 AI 拆解完成，例 #2：帮我做一份文件放在桌面上</div>
    <div>· #3：先看方案再执行，例 #3：整理一下我的下载文件夹</div>
    <div>· #4：自主循环完成，例 #4：把红包功能做好</div>

    ${isSases ? '<div>· *1：导入知识库，例 *1：将以下内容导入知识库，内容如下...</div>' : ''}
    <div>· 点击 🤖 切换智能体身份</div>
    <div style="margin-top:8px; text-align:right;">
      <button id="dismiss-free-mode-guide" style="background:none; border:none; color:#007aff; cursor:pointer;">不再显示</button>
    </div>
  `;
  container.appendChild(guide);
  document.getElementById('dismiss-free-mode-guide').addEventListener('click', () => {
    localStorage.setItem('sases_free_mode_guide_dismissed', '1');
    guide.remove();
  });
}