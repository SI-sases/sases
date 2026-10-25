// static/modules/api.js

const BASE_URL = '';

function getToken() {
  return localStorage.getItem('sases_token') || '';
}

async function request(url, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const text = await response.text();
    let errorText = text;
    try {
      const errData = JSON.parse(text);
      if (typeof errData === 'string') {
        errorText = errData;
      } else if (errData.detail) {
        errorText = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      } else {
        errorText = JSON.stringify(errData);
      }
    } catch {
      errorText = text;
    }
    const error = new Error(errorText || `HTTP ${response.status}`);
    error.status = response.status;
    error.data = text;
    throw error;
  }

  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  // 认证
  login: (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return fetch('/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString()
    }).then(async resp => {
      const text = await resp.text();
      if (!resp.ok) {
        let errText = text;
        try { errText = JSON.parse(text).detail || text; } catch {}
        throw new Error(errText || `登录失败 (${resp.status})`);
      }
      return JSON.parse(text);
    });
  },
  register: (username, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ username, password }) }),
  getMe: () => request('/auth/me'),

  // 用户资料
  getUserProfile: () => request('/user/profile'),
  updateUserProfile: (data) => request('/user/profile', { method: 'PUT', body: JSON.stringify(data) }),

  // 模型管理
  listModels: () => request('/models/list'),
  addApiKey: (data) => request('/models/api-key', { method: 'POST', body: JSON.stringify(data) }),
  addLocalModel: (data) => request('/models/local', { method: 'POST', body: JSON.stringify(data) }),
  updateModelShare: (modelId, data) => request(`/models/${modelId}/share`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteModel: (modelId) => request(`/models/${modelId}`, { method: 'DELETE' }),

  // 智能体
  listMyAgents: () => request('/agents/list'),
  listFriendAgents: () => request('/agents/friends'),
  searchAgents: (q, includeSelf = false) => request(`/agents/search?q=${encodeURIComponent(q)}&include_self=${includeSelf}`),
  sendFriendRequest: (agentId) => request('/agents/friend-request', { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
  getFriendRequests: () => request('/agents/friend-requests'),
  acceptFriendRequest: (requestId) => request('/agents/friend-requests/accept', { method: 'POST', body: JSON.stringify({ request_id: requestId }) }),
  rejectFriendRequest: (requestId) => request('/agents/friend-requests/reject', { method: 'POST', body: JSON.stringify({ request_id: requestId }) }),
  callAgent: (agentId, query) => request('/agents/call', { method: 'POST', body: JSON.stringify({ agent_id: agentId, query }) }),

  // 消息
  sendMessage: (data) => request('/messages/send', { method: 'POST', body: JSON.stringify(data) }),
  listConversations: () => request('/messages/conversations'),
  getConversationMessages: (conversationId, limit = 50, offset = 0) => request(`/messages/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`),
  markConversationRead: (conversationId) => request(`/messages/${conversationId}/read`, { method: 'POST' }),
  togglePinConversation: (conversationId, pinned) => request(`/messages/${conversationId}/pin`, { method: 'POST', body: JSON.stringify({ pinned }) }),
  deleteConversation: (conversationId) => request(`/messages/${conversationId}`, { method: 'DELETE' }),

  // 建议回复
  suggestReply: (query) => request('/agent/chat', { method: 'POST', body: JSON.stringify({ query }) }),

  // 工作模式（指令执行）
  workExecute: (conversationId, command, senderAgentId = null) => request('/work/execute', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: conversationId,
      command: command,
      sender_agent_id: senderAgentId
    })
  }),
  getWorkLogs: (limit = 50) => request(`/work/logs?limit=${limit}`),

  // 指挥官任务
  commanderExecute: (conversationId, task, senderAgentId = null) => request('/commander/execute', {
    method: 'POST',
    body: JSON.stringify({
      conversation_id: conversationId,
      task: task,
      sender_agent_id: senderAgentId
    })
  }),

  // 质量保障
  submitFalsify: (title, detail, sourceId = null) => request('/quality/falsify', {
    method: 'POST',
    body: JSON.stringify({ title, detail, source_id: sourceId })
  }),
  listQualityIssues: (source = null, mine = false, limit = 50) => {
    let url = `/quality/issues?limit=${limit}&mine=${mine}`;
    if (source) url += `&source=${encodeURIComponent(source)}`;
    return request(url);
  },
  getQualityStatistics: () => request('/quality/statistics'),
  getRescuePool: (limit = 20) => request(`/quality/rescue-pool?limit=${limit}`),
  triggerDebugScan: (sampleLimit = 20) => request(`/quality/debug/scan?sample_limit=${sampleLimit}`, { method: 'POST' }),

  // 解救任务（旧表，保留兼容）
  generateRescueTasks: (limit = 10) => request('/rescue/generate', { method: 'POST', body: JSON.stringify({ limit }) }),
  listRescueTasks: (limit = 50) => request(`/rescue/tasks?limit=${limit}`),
  getRescueTask: (taskId) => request(`/rescue/tasks/${taskId}`),
  acceptRescueTask: (taskId, agentId = null) => request('/rescue/accept', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId, agent_id: agentId })
  }),
  analyzeRescueTask: (taskId, agentId = null, previousFailure = null) => request('/rescue/analyze', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId, agent_id: agentId, previous_failure: previousFailure })
  }),
  verifyRescueTask: (taskId) => request('/rescue/verify', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId })
  }),
  abandonRescueTask: (taskId) => request('/rescue/abandon', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId })
  }),
  getMyRescueTasks: (limit = 50) => request(`/rescue/my-tasks?limit=${limit}`),
  getRescueStatistics: () => request('/rescue/statistics'),

  // 云宠战役
  listYunchongTasks: () => request('/yunchong/tasks'),
  getYunchongRefreshInfo: () => request('/yunchong/refresh-info'),
  refreshYunchongTasks: () => request('/yunchong/refresh', { method: 'POST' }),
  getYunchongTask: (taskId) => request(`/yunchong/tasks/${taskId}`),
  acceptYunchongTask: (taskId) => request('/yunchong/accept', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId })
  }),
  abandonYunchongTask: (taskId) => request('/yunchong/abandon', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId })
  }),
  analyzeYunchongTask: (taskId, agentId = null, previousFailure = null, useOfficial = true) => request('/yunchong/analyze', {
    method: 'POST',
    body: JSON.stringify({
      task_id: taskId,
      agent_id: agentId,
      previous_failure: previousFailure,
      use_official: useOfficial
    })
  }),
  verifyYunchongTask: (taskId) => request('/yunchong/verify', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId })
  }),
  getYunchongOfficialUsage: () => request('/yunchong/official-agent/usage'),
  getMyYunchongTasks: (limit = 50) => request(`/yunchong/my-tasks?limit=${limit}`),

  // 宠物系统
  getPetList: (limit = 100) => request(`/pet/list?limit=${limit}`),
  getPet: (petId) => request(`/pet/${petId}`),
  feedPet: (petId, expAmount = 10) => request('/pet/feed', {
    method: 'POST',
    body: JSON.stringify({ pet_id: petId, exp_amount: expAmount })
  }),
  evolvePet: (petId) => request('/pet/evolve', {
    method: 'POST',
    body: JSON.stringify({ pet_id: petId })
  }),
  strengthenPet: (petId, attribute = 'strength') => request('/pet/strengthen', {
    method: 'POST',
    body: JSON.stringify({ pet_id: petId, attribute })
  }),
  awakenPet: (petId) => request('/pet/awaken', {
    method: 'POST',
    body: JSON.stringify({ pet_id: petId })
  }),
  releasePet: (petId) => request('/pet/release', {
    method: 'POST',
    body: JSON.stringify({ pet_id: petId })
  }),
  getAllGameResources: () => request('/pet/resources/all'),
  getPetStatistics: () => request('/pet/statistics/overview'),

  // 基地系统
  getBaseOverview: () => request('/base/overview'),
  listBaseFacilities: () => request('/base/facilities'),
  getBaseFacility: (facilityType) => request(`/base/facility/${encodeURIComponent(facilityType)}`),
  getBaseUpgradeCost: (facilityType) => request(`/base/facility/${encodeURIComponent(facilityType)}/upgrade-cost`),
  upgradeBaseFacility: (facilityType) => request('/base/upgrade', {
    method: 'POST',
    body: JSON.stringify({ facility_type: facilityType })
  }),
  collectBaseOutput: (facilityType) => request('/base/collect', {
    method: 'POST',
    body: JSON.stringify({ facility_type: facilityType })
  }),
  assignBaseCaptain: (facilityType, petId) => request('/base/assign-captain', {
    method: 'POST',
    body: JSON.stringify({ facility_type: facilityType, pet_id: petId })
  }),
  assignBaseMember: (facilityType, petId) => request('/base/assign-member', {
    method: 'POST',
    body: JSON.stringify({ facility_type: facilityType, pet_id: petId })
  }),
  removeBaseMember: (facilityType, petId) => request('/base/remove-member', {
    method: 'POST',
    body: JSON.stringify({ facility_type: facilityType, pet_id: petId })
  }),

  // 数据库备份
  listBackups: () => request('/backup/list'),
  createBackup: () => request('/backup/create', { method: 'POST' }),
  cleanupBackups: () => request('/backup/cleanup', { method: 'POST' }),

  // 新手引导
  getOnboardingStatus: () => request('/onboarding/status'),
  completeOnboardingStep: (action) => request('/onboarding/complete-step', { method: 'POST', body: JSON.stringify({ action }) }),
  resetOnboarding: () => request('/onboarding/reset', { method: 'POST' }),

  // 官方算力服务
  getComputeBalance: () => request('/compute/balance'),
  listComputeServices: () => request('/compute/services'),
  getComputePricing: () => request('/compute/pricing'),
  // rechargeCompute 已移除（v0.19.0 前端不再暴露充值入口）
  exchangeCompute: (creditsAmount) => request('/compute/exchange', { method: 'POST', body: JSON.stringify({ credits_amount: creditsAmount }) }),
  consumeCompute: (serviceKey, detail = '') => request('/compute/consume', { method: 'POST', body: JSON.stringify({ service_key: serviceKey, detail }) }),
  getComputeTransactions: (limit = 50) => request(`/compute/transactions?limit=${limit}`),

  // 记忆库
  rememberMemory: (data) => request('/memory/remember', { method: 'POST', body: JSON.stringify(data) }),
  recallMemory: (query, top_k = 5, memory_type = null) => request('/memory/recall', {
    method: 'POST',
    body: JSON.stringify({ query, top_k, memory_type })
  }),
  getMemoryByType: (memory_type, top_k = 5) => request(`/memory/type/${memory_type}?top_k=${top_k}`),
  deleteMemory: (memoryId) => request(`/memory/${memoryId}`, { method: 'DELETE' }),

  // 积分
  getBalance: () => request('/credits/balance'),
  getCreditHistory: (limit = 50) => request(`/credits/history?limit=${limit}`),
  exchangeCredits: (credits) => request('/credits/exchange', { method: 'POST', body: JSON.stringify({ credits }) }),
  stakeCredits: (credits, duration_days) => request('/credits/stake', { method: 'POST', body: JSON.stringify({ credits, duration_days }) }),

  // 知识库
  listKnowledge: () => request('/knowledge/list'),
  deleteMyDoc: (sourceFile) => request('/knowledge/my-docs/' + encodeURIComponent(sourceFile), { method: 'DELETE' }),
  deleteMyDoc: (sourceFile) => request('/knowledge/my-docs/' + encodeURIComponent(sourceFile), { method: 'DELETE' }),
  deleteMyDoc: (sourceFile) => request('/knowledge/my-docs/' + encodeURIComponent(sourceFile), { method: 'DELETE' }),

  // 统计
  getLeaderboard: () => request('/stats/leaderboard'),
  getHarnessModules: () => request('/stats/harness-modules'),

  // 搜索
  globalSearch: (q) => request(`/search/all?q=${encodeURIComponent(q)}`),

  // AI 圈
  getAiCirclePosts: () => request('/ai-circle/posts'),
  createAiCirclePost: (content, post_type = 'daily') => request('/ai-circle/posts', { method: 'POST', body: JSON.stringify({ content, post_type }) }),

  // 数据导出删除
  exportUserData: () => request('/export/data'),
  deleteUserCloudData: () => request('/export/delete-data', { method: 'DELETE' }),

  // 交易市场
  listMarketOrders: (status = null) => request(`/market/orders${status ? `?status=${status}` : ''}`),
  createMarketOrder: (order_type, description, price) => request('/market/orders', { method: 'POST', body: JSON.stringify({ order_type, description, price }) }),
  acceptMarketOrder: (order_id) => request('/market/orders/accept', { method: 'POST', body: JSON.stringify({ order_id }) }),

  // 智维空间
  getWisdomSpaceNodes: () => request('/wisdom-space/nodes'),

  // 群聊
  createGroup: (name) => request('/group/create', { method: 'POST', body: JSON.stringify({ name }) }),

  quitGroup: (groupId) => request('/group/quit', { method: 'POST', body: JSON.stringify({ groupId }) }),
  dismissGroup: (groupId) => request('/group/dismiss', { method: 'POST', body: JSON.stringify({ groupId }) }),

  exitGroup: (groupId) => request('/group/exit', { method: 'POST', body: JSON.stringify({ groupId }) }),
  dismissGroup: (groupId) => request('/group/dismiss', { method: 'POST', body: JSON.stringify({ groupId }) }),
  inviteToGroup: (group_id, username_or_id) => request('/group/invite', { method: 'POST', body: JSON.stringify({ group_id, username_or_id }) }),
  listMyGroups: () => request('/group/list'),
  getGroupInfo: (group_id) => request(`/group/${group_id}/info`),
  getGroupMessages: (group_id) => request(`/group/${group_id}/messages`),

  getGroupTasks: (group_id, status) => request(`/group/${group_id}/tasks${status ? '?status=' + status : ''}`),

  getActiveGroupRedPackets: (group_id) => request(`/group/${group_id}/red-packets/active`),
  sendGroupMessage: (group_id, content, agent_id = null) => request(`/group/${group_id}/messages`, { method: 'POST', body: JSON.stringify({ content, agent_id }) }),
  getGroupMembers: (group_id) => request(`/group/${group_id}/members`),
  getGroupCredits: (group_id) => request(`/group/${group_id}/credits`),
  markGroupRead: (group_id) => request(`/group/${group_id}/read`, { method: 'POST' }),

  markGroupRead: (group_id) => request(`/group/${group_id}/read`, { method: 'POST' }),

  togglePinGroup: (group_id, pinned) => request(`/group/${group_id}/pin`, { method: 'POST', body: JSON.stringify({ pinned }) }),

  removeGroupMember: (group_id, username_or_id) => request(`/group/${group_id}/remove-member`, { method: 'POST', body: JSON.stringify({ username_or_id }) }),
  setGroupMode: (group_id, mode) => request(`/group/${group_id}/mode`, { method: 'POST', body: JSON.stringify({ mode }) }),

  // 转账红包
  transferCredits: (receiver_id, amount, message, conversation_id) => request('/transfer/transfer', {
    method: 'POST',
    body: JSON.stringify({ receiver_id, amount, message, conversation_id })
  }),
  sendRedPacket: (receiver_id, amount, message, conversation_id) => request('/transfer/red-packet', {
    method: 'POST',
    body: JSON.stringify({ receiver_id, amount, message, conversation_id })
  }),
  getPendingRedPackets: () => request('/transfer/pending'),
  claimRedPacket: (tx_id) => request('/transfer/claim', { method: 'POST', body: JSON.stringify({ tx_id }) }),
  uploadFile: async (file) => {
    const b64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    return request('/upload/file', {
      method: 'POST',
      body: JSON.stringify({ original_name: file.name, base64_data: b64 })
    });
  },



  uploadImage: async (file) => {
    const b64 = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    return request('/upload/image', {
      method: 'POST',
      body: JSON.stringify({ original_name: file.name, base64_data: b64 })
    });
  },


  cancelRun: (runId) => request('/supervisor/cancel', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId })
  }),

  confirmRun: (runId) => request('/supervisor/confirm', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId })
  }),
  rejectRun: (runId) => request('/supervisor/reject', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId })
  }),


  getRedPacketDetail: (tx_id) => request(`/transfer/detail/${tx_id}`),
};