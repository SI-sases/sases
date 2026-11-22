# SASES 未完成事项与执行状态

更新时间：2026-11-23
基线 commit：744cdf3

## 已完成

- P0-1 ~ P0-9：多子智能体、后台执行、预算、重试上限、优先级、本地模型
- P1-1 ~ P1-7：重启恢复、队列恢复、WebSocket 刷新、取消、超时、优先级、多 worker
- P2-1：commander 路由改为显式 opt-in
- P2-2：executor 后台启动已移除
- P2-3：旧 plan_task 启动续跑已停用
- P3-1：goal 创建/列表/暂停/取消 API
- P3-3：schedule 失败指数 backoff
- P3-4：schedule 幂等
- P3-5：审批 `ON CONFLICT(run_id, step_id)` 幂等
- P4-1/P4-4：stream 入口按任务分流，读文件走 strict 只读工具
- P5-2：conversations.skill_ids 持久化并在前端恢复
- P5-3：skill_invalid / DSH 未配置提示

## 未完成

### P3-2
- goal 3 轮真实执行验收
- 预算耗尽后的 goal 状态收敛

### P4-2 / P4-3
- agent_loop token 级流式
- 群聊 / A2A 流式

### P6
- 剩余 i18n：group_chat.js、chat.js、me_wallet.js、main.js、discover.js、contacts.js 等
- 英文全页截图验收

### P7
- 自动测试与 CI
- 真实长任务回归
- 旧数据只读策略
- 文档完整同步

### A1/A2
- 多文件任务逐文件独立事务
- partial 前端截图/布局校验

### P8
- video_edit / CUA：缺少 FFmpeg / Windows-MCP / CUA，blocked

## 执行原则

- 不新增表、不新增框架
- 不再恢复四角色默认链
- 每个文件写完立即 verify
- 失败回滚当前文件，不污染其他文件
- 旧表只读，不删历史数据
