# group_chat.js 拆分状态

## 已完成（7 个模块，981 行）

| 模块 | 文件 | 行数 |
|------|------|------|
| Toast | group_toast.js | 22 |
| 群文件 | group_file_ui.js | 50 |
| 群知识库 | group_knowledge_ui.js | 157 |
| 群红包对话框 | group_redpacket_ui.js | 117 |
| 群任务 | group_task_ui.js | 134 |
| 蜂群管理 | group_swarm_ui.js | 193 |
| 群管理 | group_manage_ui.js | 308 |

## 主文件状态
- 原：2635 行 / 116KB
- 现：约 1640 行 / 72KB
- 减少：约 36%

## 有意保留在主文件的函数

| 函数 | 原因 |
|------|------|
| openGroupSettings | 高耦合，returnAction 链路复杂，拆错会断返回 |
| openGroupRedPacket | 和 openGroupRedPacketDialog 逻辑分裂，但不影响功能 |
| openGroupReportQueue | 独立但价值一般，拆出去收益小 |
| openGroupAgentPickerForReply | 35 行，不值得拆 |
| openGroupNameEditor 等小工具 | 30 行，不值得拆 |

## 已知问题
- openGroupRedPacket 和 openGroupRedPacketDialog 分散在两个文件
- 尝试拆分 openGroupRedPacket 到 group_redpacket_ui.js 失败（delete_block 不返回删除内容，三者只能插入空骨架）

## 未来如果要拆
- openGroupReportQueue（100 行，独立性强）
- 不建议拆 openGroupSettings（风险高于收益）

## 工具状态
- delete_block：v1.3，可安全删除代码块（含括号计数、白名单、回滚）
- split_block：v1.3，原子拆分 + 自动补 import + 单行函数支持
- file_patch：v2.9.1，幂等检查（skipped=already_exists）

## 拆分操作规范
参见 docs/SPLIT_PLAYBOOK.md
