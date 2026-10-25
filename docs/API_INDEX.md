# SASES API 接口清单
共 39 个路由文件
共 222 个接口

## agent_routes.py (9 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/agents/list` | list_my_agents |  |
| GET | `/agents/friends` | list_friend_agents |  |
| GET | `/agents/search` | search_agents |  |
| POST | `/agents/friend-request` | send_friend_request |  |
| GET | `/agents/friend-requests` | get_received_friend_requests |  |
| POST | `/agents/friend-requests/accept` | accept_friend_request |  |
| POST | `/agents/friend-requests/reject` | reject_friend_request |  |
| POST | `/agents/call` | call_agent |  |
| POST | `/agents/chat` | api_suggest_reply | 根据智能体生成建议回复（不入库） |

## agi_routes.py (1 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/agi/execute` | execute_agi |  |

## ai_circle_routes.py (2 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/ai-circle/posts` | get_posts |  |
| POST | `/ai-circle/posts` | create_post |  |

## auth_routes.py (4 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/token` | login_for_access_token |  |
| POST | `/auth/login` | login_json |  |
| POST | `/auth/register` | register |  |
| GET | `/auth/me` | get_me |  |

## backup_routes.py (3 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/backup/list` | list_backups | 列出所有备份文件 |
| POST | `/backup/create` | create_backup | 手动创建一次备份 |
| POST | `/backup/cleanup` | cleanup_backups | 清理超过保留天数的备份 |

## base_routes.py (9 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/base/overview` | get_overview | 获取基地总览：所有设施、等级、产出、任职情况 |
| GET | `/base/facilities` | list_facilities | 列出所有设施 |
| GET | `/base/facility/{facility_type}` | get_facility | 获取单个设施详情 |
| GET | `/base/facility/{facility_type}/upgrade-cost` | get_upgrade_cost | 查询升级消耗 |
| POST | `/base/upgrade` | upgrade_facility | 升级设施 |
| POST | `/base/collect` | collect_output | 收取设施产出 |
| POST | `/base/assign-captain` | assign_captain | 任命设施队长 |
| POST | `/base/assign-member` | assign_member | 添加设施队员 |
| POST | `/base/remove-member` | remove_member | 移除设施队员 |

## chat_routes.py (1 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/agent/chat` | chat |  |

## commander_routes.py (1 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/commander/execute` | execute_task |  |

## compute_routes.py (7 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/compute/balance` | get_balance | 获取算力余额 |
| GET | `/compute/services` | list_services | 列出所有官方算力服务 |
| GET | `/compute/pricing` | get_pricing | 获取算力定价信息 |
| POST | `/compute/recharge` | recharge |  |
| POST | `/compute/exchange` | exchange | 用种子积分兑换算力 |
| POST | `/compute/consume` | consume | 扣减算力（消费官方服务） |
| GET | `/compute/transactions` | get_transactions | 获取算力交易记录 |

## credit_routes.py (4 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/credits/balance` | get_balance |  |
| GET | `/credits/history` | get_history |  |
| POST | `/credits/exchange` | exchange_credits |  |
| POST | `/credits/stake` | stake_credits |  |

## export_routes.py (1 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/export/data` | export_data |  |

## group_routes.py (63 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/group/group/{group_id}/leave` | api_leave_group |  |
| POST | `/group/group/{group_id}/dismiss` | api_dismiss_group |  |
| POST | `/group/create` | create_group |  |
| POST | `/group/invite` | invite_to_group |  |
| GET | `/group/list` | list_my_groups |  |
| GET | `/group/{group_id}/info` | get_group_info |  |
| GET | `/group/{group_id}/messages` | get_group_messages |  |
| POST | `/group/{group_id}/messages` | send_group_message |  |
| GET | `/group/{group_id}/members` | get_group_members |  |
| GET | `/group/{group_id}/credits` | get_group_credits |  |
| POST | `/group/{group_id}/remove-member` | remove_member |  |
| POST | `/group/{group_id}/pin` | toggle_pin |  |
| POST | `/group/{group_id}/read` | mark_read |  |
| POST | `/group/{group_id}/mode` | set_group_mode |  |
| POST | `/group/{group_id}/tasks/publish` | api_publish_task |  |
| GET | `/group/{group_id}/tasks` | api_list_tasks |  |
| GET | `/group/tasks/{task_id}` | api_get_task |  |
| POST | `/group/tasks/{task_id}/submit` | api_submit_task |  |
| POST | `/group/tasks/{task_id}/select` | api_select_task |  |
| POST | `/group/tasks/{task_id}/reject` | api_reject_task |  |
| POST | `/group/{group_id}/stake` | api_stake |  |
| POST | `/group/{group_id}/stake/withdraw` | api_withdraw_stake |  |
| GET | `/group/{group_id}/stakes` | api_list_stakes |  |
| GET | `/group/{group_id}/pool` | api_group_pool |  |
| POST | `/group/{group_id}/red-packet/config` | api_config_red_packet |  |
| POST | `/group/{group_id}/red-packet/send` | api_send_red_packet |  |
| POST | `/group/{group_id}/red-packets/create` | api_create_group_red_packet |  |
| POST | `/group/red-packets/{packet_id}/claim` | api_claim_group_red_packet |  |
| GET | `/group/red-packets/{packet_id}` | api_get_group_red_packet |  |
| GET | `/group/{group_id}/red-packets/active` | api_list_active_group_red_packets |  |
| GET | `/group/{group_id}/leaderboard` | api_group_leaderboard |  |
| POST | `/group/{group_id}/knowledge` | api_create_knowledge |  |
| GET | `/group/{group_id}/knowledge` | api_list_knowledge |  |
| GET | `/group/knowledge/{doc_id}` | api_get_knowledge |  |
| DELETE | `/group/knowledge/{doc_id}` | api_delete_knowledge |  |
| GET | `/group/{group_id}/report-queue` | api_list_report_queue |  |
| POST | `/group/{group_id}/report-queue` | api_add_report |  |
| POST | `/group/report-queue/{queue_id}/resolve` | api_resolve_report |  |
| POST | `/group/report-queue/{queue_id}/ignore` | api_ignore_report |  |
| GET | `/group/{group_id}/swarm/status` | api_swarm_status |  |
| POST | `/group/{group_id}/swarm/toggle` | api_swarm_toggle |  |
| GET | `/group/{group_id}/resource-pool` | api_list_resource_pool |  |
| POST | `/group/{group_id}/resource-pool/bind` | api_bind_agent_model |  |
| POST | `/group/{group_id}/resource-pool/unbind` | api_unbind_agent |  |
| GET | `/group/{group_id}/resource-usage` | api_resource_usage |  |
| GET | `/group/{group_id}/quota-check` | api_quota_check |  |
| GET | `/group/{group_id}/admins` | api_list_group_admins |  |
| POST | `/group/{group_id}/members/role` | api_set_member_role |  |
| POST | `/group/{group_id}/ai-suggest` | api_group_ai_suggest |  |
| GET | `/group/{group_id}/announcement` | api_get_announcement |  |
| POST | `/group/{group_id}/announcement` | api_set_announcement |  |
| POST | `/group/{group_id}/transfer-owner` | api_transfer_owner |  |
| GET | `/group/{group_id}/invite-confirm` | api_get_invite_confirm |  |
| POST | `/group/{group_id}/invite-confirm` | api_set_invite_confirm |  |
| GET | `/group/{group_id}/pending-invites` | api_list_pending_invites |  |
| POST | `/group/pending-invites/{pending_id}/approve` | api_approve_invite |  |
| POST | `/group/pending-invites/{pending_id}/reject` | api_reject_invite |  |
| GET | `/group/{group_id}/files` | api_list_group_files |  |
| PATCH | `/group/{group_id}/name` | api_update_group_name |  |
| PATCH | `/group/{group_id}/nickname` | api_set_nickname |  |
| PATCH | `/group/{group_id}/mute` | api_toggle_mute |  |
| GET | `/group/{group_id}/search-messages` | api_search_group_messages |  |
| POST | `/group/red-packets/expire` | api_expire_group_red_packets |  |

## harness_routes.py (2 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/harness/modules` | get_modules |  |
| POST | `/harness/execute` | execute |  |

## hive_routes.py (6 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/hive/info` | hive_info |  |
| GET | `/hive/ping` | hive_ping | 接收 peer 的群消息，写本地影子群消息。global_msg_id 去重。 |
| POST | `/hive/sync/message` | sync_message | 接收 peer 的群消息，写本地影子群消息。global_msg_id 去重。 |
| POST | `/hive/sync/member` | sync_member | 接收 peer 的成员邀请通知，写本地影子群成员 |
| POST | `/hive/sync/member-remove` | sync_member_remove | 接收 peer 的成员移除通知 |
| POST | `/hive/sync/group` | sync_group | 接收 peer 的群创建通知，写本地影子群 + 写群主为成员 |

## hive_task_routes.py (3 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/hive/sync/task` | sync_task | 接收 peer 的群任务发布通知 |
| POST | `/hive/sync/submission` | sync_submission | 接收 peer 的方案提交同步 |
| POST | `/hive/sync/task-result` | sync_task_result | 接收 peer 的任务结果同步 |

## knowledge_routes.py (4 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/knowledge/my-docs` | list_my_docs |  |
| GET | `/knowledge/my-docs/{source_file:path}` | get_my_doc |  |
| DELETE | `/knowledge/my-docs/{source_file:path}` | delete_my_doc |  |
| GET | `/knowledge/list` | list_knowledge |  |

## market_routes.py (3 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/market/orders` | list_orders |  |
| POST | `/market/orders` | create_order |  |
| POST | `/market/orders/accept` | accept_order |  |

## memory_routes.py (4 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/memory/remember` | remember |  |
| POST | `/memory/recall` | recall |  |
| GET | `/memory/type/{memory_type}` | recall_by_type |  |
| DELETE | `/memory/{memory_id}` | forget |  |

## message_routes.py (7 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/messages/conversations` | list_conversations |  |
| POST | `/messages/conversations` | create_conversation |  |
| GET | `/messages/conversations/{conversation_id}/messages` | get_messages |  |
| POST | `/messages/send` | send_message |  |
| POST | `/messages/{conversation_id}/read` | mark_read |  |
| POST | `/messages/{conversation_id}/pin` | toggle_pin |  |
| DELETE | `/messages/{conversation_id}` | delete_conversation |  |

## model_routes.py (5 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/models/api-key` | add_api_key |  |
| POST | `/models/local` | add_local_model |  |
| GET | `/models/list` | list_models |  |
| PATCH | `/models/{model_id}/share` | update_share_settings |  |
| DELETE | `/models/{model_id}` | delete_model |  |

## onboarding_routes.py (3 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/onboarding/status` | get_status | 获取当前新手引导状态 |
| POST | `/onboarding/complete-step` | complete_step | 上报完成某个动作，系统会自动检查是否匹配当前引导任务 |
| POST | `/onboarding/reset` | reset | 重置引导（测试用） |

## pet_routes.py (10 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/pet/list` | list_pets | 获取我的所有宠物 |
| GET | `/pet/{pet_id}` | get_pet | 获取宠物详情 |
| POST | `/pet/feed` | feed_pet | 喂养宠物 |
| POST | `/pet/evolve` | evolve_pet | 进化宠物 |
| POST | `/pet/strengthen` | strengthen_pet | 强化宠物属性 |
| POST | `/pet/awaken` | awaken_pet | 觉醒宠物，增加技能栏 |
| POST | `/pet/release` | release_pet | 放生宠物 |
| GET | `/pet/resources/all` | get_all_resources | 获取所有游戏资源 |
| GET | `/pet/resources/{resource_type}` | get_resource | 查询单个资源数量 |
| GET | `/pet/statistics/overview` | get_statistics | 获取用户宠物统计 |

## pollination_routes.py (2 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/pollination/submit` | submit_pollination |  |
| POST | `/pollination/falsify` | submit_falsify |  |

## quality_routes.py (8 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/quality/falsify` | submit_falsify |  |
| GET | `/quality/issues` | list_issues |  |
| GET | `/quality/issues/{issue_id}` | get_issue |  |
| POST | `/quality/issues/{issue_id}/status` | update_issue_status |  |
| GET | `/quality/rescue-pool` | get_rescue_pool | 获取可转为智维空间解救任务的待处理问题 |
| GET | `/quality/statistics` | get_statistics | 手动触发一次除虫扫描（仅扫描最近 N 条） |
| POST | `/quality/debug/scan` | trigger_debug_scan | 手动触发一次除虫扫描（仅扫描最近 N 条） |
| POST | `/quality/debug/scan-all` | trigger_full_scan | 手动触发全量除虫扫描（谨慎使用，可能耗时较长） |

## rescue_routes.py (9 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/rescue/generate` | generate_tasks | 从质量保障层生成解救任务 |
| GET | `/rescue/tasks` | list_tasks | 获取所有可接取的任务 |
| GET | `/rescue/tasks/{task_id}` | get_task | 获取单个任务详情 |
| POST | `/rescue/accept` | accept_task | 接取任务 |
| POST | `/rescue/analyze` | analyze_task | 智能体分析任务，生成方案（支持申诉重试） |
| POST | `/rescue/verify` | verify_task | 验证方案，完成解救 |
| POST | `/rescue/abandon` | abandon_task | 用户主动放弃任务 |
| GET | `/rescue/my-tasks` | my_tasks | 获取我已完成/进行中的解救任务 |
| GET | `/rescue/statistics` | statistics | 解救任务统计 |

## search_routes.py (1 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/search/all` | global_search | 全局搜索：用户、智能体、知识库 |

## seed_routes.py (3 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/seeds/list` | list_seeds |  |
| POST | `/seeds/create` | create_seed |  |
| GET | `/seeds/{task_id}` | get_seed |  |

## space_routes.py (7 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/space/health` | health |  |
| POST | `/space/register_node` | register_node |  |
| POST | `/space/register_node_external` | register_node_external |  |
| GET | `/space/nodes` | list_nodes |  |
| POST | `/space/invoke` | invoke_node |  |
| POST | `/space/sync_from_peer` | sync_from_peer |  |
| POST | `/space/register_to_peer` | register_to_peer |  |

## stats_routes.py (2 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/stats/leaderboard` | get_leaderboard |  |
| GET | `/stats/harness-modules` | get_harness_modules |  |

## supervisor_routes.py (5 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/supervisor/propose` | propose |  |
| POST | `/supervisor/confirm` | confirm |  |
| POST | `/supervisor/reject` | reject |  |
| POST | `/supervisor/cancel` | cancel |  |
| GET | `/supervisor/proposed` | get_proposed |  |

## swarm_routes.py (6 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/swarm/plan` | plan |  |
| POST | `/swarm/confirm` | confirm | 用户确认或编辑草稿任务后，下发执行 |
| POST | `/swarm/cancel` | cancel |  |
| POST | `/swarm/feedback` | feedback |  |
| GET | `/swarm/reviews` | list_reviews | 查询审核日志：只返回当前用户所属会话的记录 |
| GET | `/swarm/reviews/stats` | review_stats | 审核统计：按 exec_status 和 review_result 聚合 |

## transfer_routes.py (7 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/transfer/transfer` | create_transfer |  |
| POST | `/transfer/red-packet` | create_red_packet |  |
| GET | `/transfer/pending` | get_pending_red_packets |  |
| POST | `/transfer/claim` | claim_red_packet |  |
| GET | `/transfer/history` | get_history |  |
| GET | `/transfer/detail/{tx_id}` | get_tx_detail | 查询红包详情（供领取页面显示发送者、金额等） |
| GET | `/transfer/red_packet/sent` | get_sent_red_packets | 查询当前用户已发送的红包记录 |

## upload_routes.py (2 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/upload/image` | upload_image |  |
| POST | `/upload/file` | upload_file |  |

## user_routes.py (2 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/user/profile` | get_profile |  |
| PUT | `/user/profile` | update_profile |  |

## wisdom_space_routes.py (1 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/wisdom-space/nodes` | get_nodes |  |

## work_routes.py (5 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| POST | `/work/execute` | execute_work |  |
| POST | `/work/report` | report_work_result |  |
| GET | `/work/logs` | get_logs |  |
| POST | `/work/credit/enable` | enable_credit |  |
| POST | `/work/summarize` | summarize_work_logs |  |

## yunchong_routes.py (10 个接口)
| 方法 | 路径 | 函数 | 说明 |
|------|------|------|------|
| GET | `/yunchong/tasks` | list_tasks | 获取当前批次的地图任务，需要时自动刷新 |
| GET | `/yunchong/refresh-info` | get_refresh_info | 获取刷新倒计时信息 |
| POST | `/yunchong/refresh` | manual_refresh | 手动刷新任务批次 |
| GET | `/yunchong/tasks/{task_id}` | get_task | 获取任务详情 |
| POST | `/yunchong/accept` | accept_task | 接取任务，扣除能量（种子积分） |
| POST | `/yunchong/abandon` | abandon_task | 放弃任务 |
| GET | `/yunchong/official-agent/usage` | get_official_agent_usage | 查询官方助手使用情况 |
| POST | `/yunchong/analyze` | analyze_task | 分析任务，生成方案 |
| POST | `/yunchong/verify` | verify_task | 验证方案，完成解救 |
| GET | `/yunchong/my-tasks` | my_tasks | 获取我已完成/进行中的任务 |
