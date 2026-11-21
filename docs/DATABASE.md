# SASES 数据库结构

共 107 张表

## agent_friendships (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| friend_agent_id | TEXT |  |  |
| target_user_id | INTEGER |  |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| friend_mode | TEXT | 'normal' |  |
| auth_token | TEXT |  |  |

## agent_messages (96 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| conversation_id | INTEGER |  |  |
| run_id | INTEGER |  |  |
| seq | INTEGER |  |  |
| role | TEXT |  |  |
| content | TEXT |  |  |
| tool_calls | TEXT |  |  |
| tool_call_id | TEXT |  |  |
| created_at | TEXT |  |  |
| compacted | INTEGER | 0 |  |

## agent_pending_tools (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| step_id | TEXT |  |  |
| tool_call_id | TEXT |  |  |
| tool_id | TEXT |  |  |
| args | TEXT |  |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT |  |  |

## agent_questions (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| conversation_id | INTEGER |  |  |
| run_id | INTEGER |  |  |
| question | TEXT |  |  |
| status | TEXT | 'pending' |  |
| answer | TEXT |  |  |
| created_at | TEXT |  |  |
| answered_at | TEXT |  |  |

## agent_summary (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| conversation_id | INTEGER |  |  |
| covered_until_id | INTEGER |  |  |
| summary | TEXT |  |  |
| created_at | TEXT |  |  |
| summary_message_id | INTEGER |  |  |
| tokens_before | INTEGER |  |  |
| tokens_after | INTEGER |  |  |
| reason | TEXT |  |  |

## ai_circle_posts (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| agent_id | TEXT |  |  |
| owner_user_id | INTEGER |  |  |
| content | TEXT |  |  |
| post_type | TEXT | 'daily' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## airdrop_batches (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| batch_no | TEXT |  |  |
| total_amount | REAL | 0 |  |
| per_user | REAL | 0 |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT |  |  |
| executed_at | TEXT |  |  |

## api_call_outbox (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| request_id | TEXT |  |  |
| tool_id | TEXT |  |  |
| provider_node | TEXT |  |  |
| params | TEXT |  |  |
| context_hash | TEXT |  |  |
| tool_version_snapshot | TEXT |  |  |
| status | TEXT | 'pending' |  |
| retries | INTEGER | 0 |  |
| next_retry_at | TEXT |  |  |
| last_error | TEXT |  |  |
| result | TEXT |  |  |
| created_at | TEXT |  |  |
| updated_at | TEXT |  |  |

## api_keys (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| provider | TEXT |  |  |
| api_key_encrypted | TEXT |  |  |
| priority | INTEGER | 1 |  |
| is_active | INTEGER | 1 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## api_registry (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| tool_id | TEXT |  |  |
| name | TEXT |  |  |
| description | TEXT |  |  |
| provider_node | TEXT | 'node-A' |  |
| endpoint | TEXT |  |  |
| method | TEXT | 'POST' |  |
| task_mode | TEXT | 'sync' |  |
| params_schema | TEXT |  |  |
| unit_price | REAL | 0 |  |
| price_unit | TEXT | 'seed_credits' |  |
| provider_pubkey | TEXT |  |  |
| provider_signature | TEXT |  |  |
| total_calls | INTEGER | 0 |  |
| success_calls | INTEGER | 0 |  |
| avg_latency_ms | INTEGER | 0 |  |
| status | TEXT | 'active' |  |
| origin_node | TEXT |  |  |
| hlc_ts | TEXT |  |  |
| created_at | TEXT |  |  |
| updated_at | TEXT |  |  |

## approvals (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| step_id | TEXT |  |  |
| tool_id | TEXT |  |  |
| decision | TEXT | 'pending' |  |
| scope | TEXT | 'once' |  |
| created_at | TEXT |  |  |
| decided_at | TEXT |  |  |

## asset_snapshots (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| snapshot_date | TEXT |  | 是 |
| total_seed | REAL |  |  |
| total_compute | REAL |  |  |
| user_count | INTEGER |  |  |
| tx_count | INTEGER |  |  |
| ledger_hash | TEXT |  |  |
| created_at | TEXT |  |  |

## async_task_pool (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| handle | TEXT |  |  |
| tool_id | TEXT |  |  |
| params | TEXT |  |  |
| status | TEXT | 'submitted' |  |
| progress | INTEGER | 0 |  |
| result | TEXT |  |  |
| error | TEXT |  |  |
| run_id | INTEGER |  |  |
| conversation_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| created_at | TEXT |  |  |
| updated_at | TEXT |  |  |
| finished_at | TEXT |  |  |
| expires_at | TEXT |  |  |

## attachments (6 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| file_id | TEXT |  |  |
| user_id | INTEGER |  |  |
| original_name | TEXT |  |  |
| stored_path | TEXT |  |  |
| mime_type | TEXT |  |  |
| size_bytes | INTEGER | 0 |  |
| kind | TEXT | 'file' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## auth_meta (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| key | TEXT |  | 是 |
| value | TEXT |  |  |

## base_facilities (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| owner_user_id | INTEGER |  |  |
| facility_type | TEXT |  |  |
| level | INTEGER | 0 |  |
| captain_pet_id | INTEGER |  |  |
| member_pet_ids | TEXT |  |  |
| status | TEXT | 'idle' |  |
| last_produced_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## cognitive_rules (4 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| rule_id | TEXT |  | 是 |
| domain_main | TEXT |  |  |
| domain_sub | TEXT |  |  |
| rule_content | TEXT |  |  |
| trigger_context | TEXT |  |  |
| confidence | REAL | 0.5 |  |
| applied_count | INTEGER | 0 |  |
| success_count | INTEGER | 0 |  |
| status | TEXT | 'active' |  |
| source_pattern_ids | TEXT |  |  |
| created_at | TEXT |  |  |
| updated_at | TEXT |  |  |

## compute_transactions (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| tx_type | TEXT |  |  |
| amount | INTEGER |  |  |
| balance_after | INTEGER |  |  |
| service_key | TEXT |  |  |
| detail | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## contribution_log (179 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| action | TEXT |  |  |
| event_type | TEXT | 'manual' |  |
| points | REAL | 0 |  |
| model_source | TEXT | 'api' |  |
| model_id | TEXT |  |  |
| detail | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| origin_node | TEXT | 'node-A' |  |
| logical_clock | INTEGER | 0 |  |

## conversations (7 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| title | TEXT | '新会话' |  |
| mode | TEXT | 'normal' |  |
| unread_count | INTEGER | 0 |  |
| is_pinned | INTEGER | 0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |
| target_user_id | INTEGER |  |  |
| is_friend_chat | INTEGER | 0 |  |
| friend_mode | TEXT | 'normal' |  |
| active_task_id | TEXT |  |  |
| active_task_status | TEXT | 'idle' |  |
| active_task_snapshot | TEXT |  |  |

## credit_anchors (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| node_id | TEXT |  |  |
| ts | TEXT |  |  |
| anchor_hash | TEXT |  |  |
| record_count | INTEGER | 0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## credit_pool (72 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| amount | REAL |  |  |
| source | TEXT |  |  |
| created_at | TEXT |  |  |

## device_bindings (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| device_fingerprint | TEXT |  | 是 |
| license_key | TEXT |  |  |
| activated_at | TEXT |  |  |
| expire_at | TEXT |  |  |

## domains (5 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| domain | TEXT |  | 是 |
| pattern_count | INTEGER | 0 |  |
| active | INTEGER | 0 |  |
| activated_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## exec_audit (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| device_fp | TEXT |  |  |
| task_hash | TEXT |  |  |
| allowed | INTEGER |  |  |
| reason | TEXT |  |  |
| created_at | TEXT |  |  |

## execution_notes (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_id | TEXT |  |  |
| user_id | INTEGER |  |  |
| user_input | TEXT |  |  |
| summary | TEXT |  |  |
| outcome | TEXT | 'success' |  |
| steps_digest | TEXT |  |  |
| embedding | BLOB |  |  |
| content_hash | TEXT |  |  |
| status | TEXT | 'active' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## failed_cases (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_id | INTEGER |  |  |
| issue_id | INTEGER |  |  |
| title | TEXT |  |  |
| detail | TEXT |  |  |
| solution | TEXT |  |  |
| fail_reason | TEXT |  |  |
| verification_result | TEXT |  |  |
| severity | TEXT |  |  |
| seed_triggered | INTEGER | 0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## file_checkpoints (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| step_id | TEXT |  |  |
| path | TEXT |  |  |
| backup_path | TEXT |  |  |
| sha_before | TEXT |  |  |
| created_at | TEXT |  |  |

## forwarded_requests (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| request_id | TEXT |  | 是 |
| node_id | TEXT |  |  |
| result_json | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## fs_observations (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| path | TEXT |  |  |
| sha256 | TEXT |  |  |
| observed_at | TEXT |  |  |

## game_resources (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| owner_user_id | INTEGER |  |  |
| resource_type | TEXT |  |  |
| amount | INTEGER | 0 |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## group_airdrop_log (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| airdrop_date | TEXT |  |  |
| activity_score | REAL |  |  |
| rank | INTEGER |  |  |
| amount | REAL |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_credit_log (6 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| amount | REAL |  |  |
| tx_type | TEXT |  |  |
| detail | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_invite_pending (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| inviter_id | INTEGER |  |  |
| invitee | TEXT |  |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| resolved_at | TEXT |  |  |
| resolved_by | INTEGER |  |  |

## group_members (4 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| role | TEXT | 'member' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| last_read_at | TEXT |  |  |
| origin_node | TEXT |  |  |
| user_sases_id | TEXT |  |  |
| nickname | TEXT |  |  |
| is_muted | INTEGER | 0 |  |

## group_messages (25 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| sender_id | INTEGER |  |  |
| sender_agent_id | TEXT |  |  |
| content | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| global_msg_id | TEXT |  |  |
| origin_node | TEXT |  |  |
| message_type | TEXT | 'text' |  |
| related_id | INTEGER |  |  |
| extra_data | TEXT |  |  |
| logical_clock | INTEGER | 0 |  |
| msg_type | TEXT | 'standard' |  |
| attachments | TEXT |  |  |
| hlc_ts | TEXT |  |  |

## group_red_packet_claims (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| packet_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| amount | REAL |  |  |
| claimed_at | TEXT | CURRENT_TIMESTAMP |  |

## group_red_packets (3 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| sender_id | INTEGER |  |  |
| source_type | TEXT | 'user' |  |
| total_amount | REAL |  |  |
| total_count | INTEGER |  |  |
| claimed_count | INTEGER | 0 |  |
| remaining_amount | REAL |  |  |
| message | TEXT |  |  |
| status | TEXT | 'active' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| expires_at | TEXT |  |  |
| packet_type | TEXT | 'lucky' |  |

## group_report_queue (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| question | TEXT |  |  |
| asked_by | INTEGER |  |  |
| anonymous | INTEGER | 0 |  |
| hit_knowledge_id | INTEGER |  |  |
| status | TEXT | 'pending' |  |
| resolved_kb_id | INTEGER |  |  |
| resolved_by | INTEGER |  |  |
| resolved_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_resource_pool (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| model_id | TEXT |  |  |
| daily_limit | INTEGER | 100 |  |
| enabled | INTEGER | 1 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_resource_usage (8 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| model_id | TEXT |  |  |
| tokens_used | INTEGER | 0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_stakes (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| amount | REAL |  |  |
| status | TEXT | 'active' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| withdrawn_at | TEXT |  |  |

## group_task_submissions (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_id | INTEGER |  |  |
| global_submission_id | TEXT |  |  |
| submitted_by | INTEGER |  |  |
| agent_id | TEXT |  |  |
| content | TEXT |  |  |
| content_type | TEXT | 'text' |  |
| is_disqualified | INTEGER | 0 |  |
| edited_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_tasks (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| global_task_id | TEXT |  |  |
| title | TEXT |  |  |
| description | TEXT |  |  |
| task_category | TEXT | 'text' |  |
| created_by | INTEGER |  |  |
| reward_credits | REAL | 0 |  |
| status | TEXT | 'open' |  |
| selected_submission_id | INTEGER |  |  |
| judging_deadline | TEXT |  |  |
| reject_reason | TEXT |  |  |
| last_repushed_at | TEXT |  |  |
| repush_count | INTEGER | 0 |  |
| origin_node | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| packet_type | TEXT | 'lucky' |  |

## groups (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| name | TEXT |  |  |
| owner_id | INTEGER |  |  |
| mode | TEXT | 'normal' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| global_group_id | TEXT |  |  |
| origin_node | TEXT |  |  |
| is_pinned | INTEGER | 0 |  |
| credits | REAL | 0 |  |
| staked_credits | REAL | 0 |  |
| features | TEXT | '{}' |  |
| red_packet_hour | INTEGER | 20 |  |
| red_packet_audience | TEXT | 'all' |  |
| airdrop_enabled | INTEGER | 1 |  |
| airdrop_paused_until | TEXT |  |  |
| last_red_packet_date | TEXT |  |  |
| pool_packet_amount | REAL | 0 |  |
| pool_packet_count | INTEGER | 5 |  |
| announcement | TEXT |  |  |
| logical_clock | INTEGER | 0 |  |

## intent_feedback (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| task_id | TEXT |  |  |
| original_input | TEXT |  |  |
| feedback_type | TEXT | 'false_positive' |  |
| note | TEXT |  |  |
| created_at | TEXT |  |  |

## interaction_patterns (29 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| domain | TEXT | 'general' |  |
| pattern_key | TEXT |  |  |
| pattern_type | TEXT |  |  |
| context_signature | TEXT |  |  |
| role | TEXT |  |  |
| evidence | TEXT |  |  |
| confidence | REAL | 0.5 |  |
| hit_count | INTEGER | 0 |  |
| success_count | INTEGER | 0 |  |
| fail_count | INTEGER | 0 |  |
| distinct_user_count | INTEGER | 0 |  |
| last_hit_at | TEXT |  |  |
| last_success_at | TEXT |  |  |
| status | TEXT | 'active' |  |
| source_task_id | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## knowledge_base (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task | TEXT |  |  |
| branch_a | TEXT |  |  |
| branch_b | TEXT |  |  |
| solution | TEXT |  |  |
| verified | INTEGER | 0 |  |
| source_task_id | INTEGER |  |  |
| contributor_id | INTEGER |  |  |
| hit_count | INTEGER | 0 |  |
| quality_score | INTEGER | 0 |  |
| last_used_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## knowledge_docs (3 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| scope | TEXT | 'group' |  |
| group_id | INTEGER |  |  |
| title | TEXT |  |  |
| content | TEXT |  |  |
| category | TEXT | 'doc' |  |
| tags | TEXT |  |  |
| source_type | TEXT | 'manual' |  |
| source_id | TEXT |  |  |
| contributor_id | INTEGER |  |  |
| hit_count | INTEGER | 0 |  |
| visibility | TEXT | 'group' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| updated_at | TEXT |  |  |

## ledger_versions (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| node_id | TEXT |  | 是 |
| version | INTEGER | 0 |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## license_keys (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| key_code | TEXT |  | 是 |
| key_type | TEXT |  |  |
| duration_days | INTEGER |  |  |
| seed_reward_total | REAL |  |  |
| seed_reward_daily | REAL |  |  |
| status | TEXT | 'unused' |  |
| banned_at | TEXT |  |  |
| ban_reason | TEXT |  |  |
| created_at | TEXT |  |  |
| used_at | TEXT |  |  |
| used_by | INTEGER |  |  |
| device_fp | TEXT |  |  |

## llm_usage (85 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| request_id | TEXT |  |  |
| user_id | INTEGER |  |  |
| conversation_id | INTEGER |  |  |
| model | TEXT |  |  |
| purpose | TEXT |  |  |
| prompt_tokens | INTEGER | 0 |  |
| completion_tokens | INTEGER | 0 |  |
| total_tokens | INTEGER | 0 |  |
| cached_tokens | INTEGER | 0 |  |
| created_at | TEXT |  |  |
| prefix_hash | TEXT |  |  |

## market_orders (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| order_type | TEXT |  |  |
| description | TEXT |  |  |
| price | REAL |  |  |
| status | TEXT | 'open' |  |
| accepted_by | INTEGER |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## memory_fts (266 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| content |  |  |  |
| tags |  |  |  |

## memory_fts_config (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| k |  |  | 是 |
| v |  |  |  |

## memory_fts_content (266 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| c0 |  |  |  |
| c1 |  |  |  |

## memory_fts_data (169 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| block | BLOB |  |  |

## memory_fts_docsize (266 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| sz | BLOB |  |  |

## memory_fts_idx (166 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| segid |  |  | 是 |
| term |  |  | 是 |
| pgno |  |  |  |

## messages (314 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| conversation_id | INTEGER |  |  |
| sender | TEXT |  |  |
| content | TEXT |  |  |
| sender_agent_id | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| msg_type | TEXT | 'standard' |  |
| attachments | TEXT |  |  |
| hlc_ts | TEXT |  |  |
| origin_node | TEXT |  |  |

## model_configs (7 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | TEXT |  | 是 |
| user_id | INTEGER |  |  |
| model_type | TEXT |  |  |
| name | TEXT |  |  |
| provider | TEXT |  |  |
| api_key_encrypted | TEXT |  |  |
| node_url | TEXT |  |  |
| model_name | TEXT |  |  |
| capabilities | TEXT |  |  |
| is_shared | INTEGER | 0 |  |
| visibility | TEXT | 'private' |  |
| price | REAL | 1.0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## node_registry (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| node_id | TEXT |  | 是 |
| public_key | TEXT |  |  |
| url | TEXT |  |  |
| role | TEXT |  |  |
| status | TEXT | 'active' |  |
| first_seen | TEXT | CURRENT_TIMESTAMP |  |
| last_seen | TEXT | CURRENT_TIMESTAMP |  |
| master_epoch | INTEGER | 0 |  |
| priority | INTEGER | 100 |  |

## nodes (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| node_id | TEXT |  | 是 |
| node_name | TEXT |  |  |
| role_type | TEXT | 'app_node' |  |
| public_key | TEXT |  |  |
| capabilities | TEXT |  |  |
| status | TEXT | 'offline' |  |
| last_heartbeat | TEXT |  |  |
| created_at | TEXT |  |  |

## nonce_cache (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| nonce | TEXT |  | 是 |
| expire_at | TEXT |  |  |

## official_compute_services (5 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| service_key | TEXT |  |  |
| service_name | TEXT |  |  |
| description | TEXT |  |  |
| unit_cost | INTEGER | 1 |  |
| is_active | INTEGER | 1 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## outbox (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| msg_id | TEXT |  |  |
| target_url | TEXT |  |  |
| payload | TEXT |  |  |
| headers | TEXT |  |  |
| status | TEXT | 'pending' |  |
| retry_count | INTEGER | 0 |  |
| max_retries | INTEGER | 5 |  |
| next_retry_at | TEXT |  |  |
| last_error | TEXT |  |  |
| created_at | TEXT |  |  |
| completed_at | TEXT |  |  |

## pets (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| owner_user_id | INTEGER |  |  |
| pet_name | TEXT |  |  |
| rarity | TEXT |  |  |
| camp | TEXT |  |  |
| element | TEXT |  |  |
| level | INTEGER | 1 |  |
| exp | INTEGER | 0 |  |
| stage | INTEGER | 0 |  |
| skill_slots | INTEGER | 1 |  |
| current_skills | TEXT |  |  |
| strength | INTEGER | 0 |  |
| hp | INTEGER | 0 |  |
| defense | INTEGER | 0 |  |
| is_listed | INTEGER | 0 |  |
| source_task_id | INTEGER |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## project_docs (44 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| source_file | TEXT |  |  |
| section_title | TEXT |  |  |
| section_path | TEXT |  |  |
| section_level | INTEGER | 2 |  |
| chunk_index | INTEGER | 0 |  |
| content | TEXT |  |  |
| embedding | BLOB |  |  |
| content_hash | TEXT |  |  |
| freshness_score | REAL | 1.0 |  |
| status | TEXT | 'active' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |
| user_id | INTEGER | 0 |  |

## project_docs_meta (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| source_file | TEXT |  | 是 |
| source_version | TEXT |  |  |
| chunk_count | INTEGER | 0 |  |
| file_hash | TEXT |  |  |
| imported_at | TEXT |  |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## project_fts (44 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| content |  |  |  |
| section_path |  |  |  |
| source_file |  |  |  |

## project_fts_config (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| k |  |  | 是 |
| v |  |  |  |

## project_fts_content (44 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| c0 |  |  |  |
| c1 |  |  |  |
| c2 |  |  |  |

## project_fts_data (27 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| block | BLOB |  |  |

## project_fts_docsize (44 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| sz | BLOB |  |  |

## project_fts_idx (25 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| segid |  |  | 是 |
| term |  |  | 是 |
| pgno |  |  |  |

## quality_issues (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| source | TEXT |  |  |
| source_id | TEXT |  |  |
| title | TEXT |  |  |
| detail | TEXT |  |  |
| severity | TEXT | 'low' |  |
| status | TEXT | 'pending' |  |
| user_id | INTEGER |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| cleaned_at | TEXT |  |  |
| assigned_to | TEXT |  |  |

## reconcile_issues (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| issue_type | TEXT |  |  |
| detail | TEXT |  |  |
| detected_at | TEXT |  |  |
| resolved | INTEGER | 0 |  |
| resolved_at | TEXT |  |  |
| resolved_by | TEXT |  |  |

## rescue_tasks (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| issue_id | INTEGER |  |  |
| difficulty | TEXT | 'medium' |  |
| pet_level | TEXT | 'C' |  |
| status | TEXT | 'available' |  |
| rescued_by_user_id | INTEGER |  |  |
| rescued_by_agent_id | TEXT |  |  |
| rescued_at | TEXT |  |  |
| assigned_agent_id | TEXT |  |  |
| solution | TEXT |  |  |
| verification_result | TEXT |  |  |
| attempts | INTEGER | 0 |  |
| status_detail | TEXT |  |  |
| reused_from_kb_id | INTEGER |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## rule_packs (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| name | TEXT |  |  |
| version | TEXT |  |  |
| author | TEXT |  |  |
| rules_json | TEXT |  |  |
| signature | TEXT |  |  |
| status | TEXT | 'draft' |  |
| origin_node | TEXT |  |  |
| hlc_ts | TEXT |  |  |
| created_at | TEXT |  |  |

## rule_tool_bindings (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| binding_id | INTEGER |  | 是 |
| rule_id | TEXT |  |  |
| tool_id | TEXT |  |  |
| usage_context | TEXT |  |  |
| priority | INTEGER | 0 |  |

## run_artifacts (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| conversation_id | INTEGER |  |  |
| kind | TEXT |  |  |
| path | TEXT |  |  |
| name | TEXT |  |  |
| meta | TEXT |  |  |
| created_at | TEXT |  |  |

## run_steps (8 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| step_id | TEXT |  |  |
| tool_id | TEXT |  |  |
| status | TEXT | 'pending' |  |
| attempt | INTEGER | 0 |  |
| input_hash | TEXT |  |  |
| idempotency_key | TEXT |  |  |
| lease_owner | TEXT |  |  |
| lease_until | TEXT |  |  |
| output_ref | TEXT |  |  |
| error | TEXT |  |  |
| started_at | TEXT |  |  |
| finished_at | TEXT |  |  |

## run_trace (145 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| run_id | INTEGER |  |  |
| conversation_id | INTEGER |  |  |
| seq | INTEGER |  |  |
| level | INTEGER | 1 |  |
| event_type | TEXT |  |  |
| tool | TEXT |  |  |
| status | TEXT |  |  |
| content | TEXT |  |  |
| duration_ms | INTEGER | 0 |  |
| extra | TEXT |  |  |
| created_at | TEXT |  |  |

## safety_memory (266 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| memory_type | TEXT |  |  |
| content | TEXT |  |  |
| full_data | TEXT |  |  |
| agent_id | TEXT |  |  |
| user_id | INTEGER |  |  |
| group_id | INTEGER |  |  |
| importance | REAL | 0.5 |  |
| tags | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| expires_at | TEXT |  |  |
| task_id | TEXT |  |  |
| embedding | BLOB |  |  |
| content_hash | TEXT |  |  |

## scheduled_tasks (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | TEXT |  | 是 |
| user_id | INTEGER |  |  |
| name | TEXT |  |  |
| cron_expr | TEXT |  |  |
| timezone | TEXT | 'Asia/Shanghai' |  |
| task_template | TEXT |  |  |
| task_params | TEXT |  |  |
| enabled | INTEGER | 1 |  |
| missed_policy | TEXT | 'catch_up' |  |
| failure_count | INTEGER | 0 |  |
| paused_reason | TEXT |  |  |
| last_run_at | TEXT |  |  |
| next_run_at | TEXT |  |  |
| created_at | TEXT |  |  |
| updated_at | TEXT |  |  |
| is_active | INTEGER | 1 |  |
| consecutive_failures | INTEGER | 0 |  |

## schema_version (10 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| version | INTEGER |  | 是 |
| applied_at | TEXT |  |  |

## seed_tasks (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | TEXT |  | 是 |
| description | TEXT |  |  |
| domain | TEXT |  |  |
| difficulty | TEXT | 'medium' |  |
| user_id | INTEGER |  |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## space_nodes (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| node_id | TEXT |  | 是 |
| name | TEXT |  |  |
| description | TEXT |  |  |
| node_type | TEXT | 'harness' |  |
| capabilities | TEXT |  |  |
| endpoint | TEXT |  |  |
| icon | TEXT |  |  |
| owner_id | TEXT | 'system' |  |
| registered_at | TEXT | CURRENT_TIMESTAMP |  |
| reputation | REAL | 1.0 |  |
| success_count | INTEGER | 0 |  |
| total_count | INTEGER | 0 |  |
| status | TEXT | 'unknown' |  |

## supervisor_runs (98 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| conversation_id | INTEGER |  |  |
| supervisor_id | TEXT |  |  |
| goal | TEXT |  |  |
| status | TEXT | 'running' |  |
| current_round | INTEGER | 0 |  |
| max_rounds | INTEGER | 5 |  |
| credits_used | INTEGER | 0 |  |
| history | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| finished_at | TEXT |  |  |
| task_type | TEXT |  |  |
| task_fingerprint | TEXT |  |  |
| lease_owner | TEXT |  |  |
| lease_until | TEXT |  |  |
| heartbeat_at | TEXT |  |  |
| deadline_at | TEXT |  |  |

## swarm_pending_tasks (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_id | TEXT |  |  |
| conversation_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| commander_id | TEXT |  |  |
| executor_id | TEXT |  |  |
| user_text | TEXT |  |  |
| steps | TEXT |  |  |
| results | TEXT |  |  |
| done_steps | TEXT |  |  |
| retry_count | INTEGER | 0 |  |
| is_draft | INTEGER | 0 |  |
| cancelled | INTEGER | 0 |  |
| no_plan | INTEGER | 0 |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |
| supervisor_run_id | INTEGER |  |  |
| supervisor_id | TEXT |  |  |

## swarm_reviews (157 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| step_type | TEXT |  |  |
| id | INTEGER |  | 是 |
| task_id | TEXT |  |  |
| conversation_id | INTEGER |  |  |
| step_id | INTEGER |  |  |
| command | TEXT |  |  |
| exec_status | TEXT |  |  |
| review_result | TEXT |  |  |
| review_reason | TEXT |  |  |
| output_preview | TEXT |  |  |
| created_at | TEXT |  |  |

## sync_received (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| source_node | TEXT |  |  |
| table_name | TEXT |  |  |
| record_id | TEXT |  |  |
| hlc_ts | TEXT |  |  |
| payload | TEXT |  |  |
| applied | INTEGER | 0 |  |
| created_at | TEXT |  |  |

## system_config (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| key | TEXT |  | 是 |
| value | TEXT |  |  |
| updated_at | TEXT |  |  |

## task_feedback (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_id | TEXT |  |  |
| user_id | INTEGER |  |  |
| conversation_id | INTEGER |  |  |
| task_source | TEXT |  |  |
| feedback_type | TEXT |  |  |
| rating | TEXT |  |  |
| reason_tag | TEXT |  |  |
| reason_text | TEXT |  |  |
| task_snapshot | TEXT |  |  |
| result_snapshot | TEXT |  |  |
| metadata | TEXT |  |  |
| weight | REAL | 1.0 |  |
| is_latest | INTEGER | 1 |  |
| task_alive | INTEGER | 1 |  |
| created_at | TEXT |  |  |
| updated_at | TEXT |  |  |

## tool_effects (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| idempotency_key | TEXT |  |  |
| tool_id | TEXT |  |  |
| result_json | TEXT |  |  |
| created_at | TEXT |  |  |

## tool_usage_daily (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| tool_id | TEXT |  |  |
| day | TEXT |  |  |
| calls | INTEGER | 0 |  |
| success | INTEGER | 0 |  |
| last_at | TEXT |  |  |

## transactions (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| sender_id | INTEGER |  |  |
| receiver_id | INTEGER |  |  |
| amount | REAL |  |  |
| tx_type | TEXT |  |  |
| status | TEXT | 'pending' |  |
| message | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| completed_at | TEXT |  |  |
| expires_at | TEXT |  |  |
| claimed_at | TEXT |  |  |
| origin_node | TEXT | 'node-A' |  |
| logical_clock | INTEGER | 0 |  |
| idempotency_key | TEXT |  |  |
| sender_node_id | TEXT |  |  |
| receiver_node_id | TEXT |  |  |
| credit_type | TEXT | 'credits' |  |

## user_api_configs (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| api_name | TEXT |  |  |
| api_desc | TEXT |  |  |
| endpoint | TEXT |  |  |
| method | TEXT | 'GET' |  |
| auth_type | TEXT | 'none' |  |
| auth_key_encrypted | TEXT |  |  |
| auth_header_name | TEXT | 'Authorization' |  |
| params_example | TEXT |  |  |
| response_path | TEXT |  |  |
| capability_tags | TEXT |  |  |
| status | TEXT | 'active' |  |
| created_at | TEXT |  |  |

## user_compute_balance (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| balance | INTEGER | 0 |  |
| total_purchased | INTEGER | 0 |  |
| total_consumed | INTEGER | 0 |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## user_daily_quotas (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| date | TEXT |  | 是 |
| llm_calls | INTEGER | 0 |  |
| api_cost_usd | REAL | 0 |  |
| scheduled_runs | INTEGER | 0 |  |
| comfyui_calls | INTEGER | 0 |  |

## user_frozen (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| reason | TEXT |  |  |
| frozen_at | TEXT |  |  |
| frozen_by | TEXT | 'system' |  |

## users (3 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| username | TEXT |  |  |
| password_hash | TEXT |  |  |
| sases_id | TEXT |  |  |
| credits | REAL | 0 |  |
| gender | TEXT |  |  |
| region | TEXT |  |  |
| signature | TEXT |  |  |
| onboarding_day | INTEGER | 1 |  |
| onboarding_completed | TEXT | '[]' |  |
| onboarding_started_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| state_hash | TEXT |  |  |
| tampered_flag | INTEGER | 0 |  |
| auto_pollinate_enabled | INTEGER | 1 |  |
| is_admin | INTEGER | 0 |  |
| email | TEXT |  |  |
| last_pulled_id | INTEGER | 0 |  |
| last_pulled_group_id | INTEGER | 0 |  |
| handle | TEXT |  |  |
| display_name | TEXT |  |  |

## work_logs (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| command | TEXT |  |  |
| output | TEXT |  |  |
| status | TEXT | 'success' |  |
| duration_ms | INTEGER |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## yunchong_official_agent_usage (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| used_today | INTEGER | 0 |  |
| reset_date | TEXT |  |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## yunchong_radar (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| expires_at | TEXT |  |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## yunchong_refresh_log (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| last_refresh_at | TEXT |  |  |
| current_batch_id | TEXT |  |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## yunchong_tasks (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| owner_user_id | INTEGER |  |  |
| issue_id | INTEGER |  |  |
| title | TEXT |  |  |
| detail | TEXT |  |  |
| difficulty | TEXT | 'medium' |  |
| pet_level | TEXT | 'C' |  |
| status | TEXT | 'available' |  |
| longitude | REAL | 0 |  |
| latitude | REAL | 0 |  |
| distance_meters | INTEGER | 0 |  |
| energy_cost | INTEGER | 0 |  |
| batch_id | TEXT |  |  |
| refreshed_at | TEXT |  |  |
| expires_at | TEXT |  |  |
| rescued_at | TEXT |  |  |
| rescued_by_agent_id | TEXT |  |  |
| solution | TEXT |  |  |
| verification_result | TEXT |  |  |
| attempts | INTEGER | 0 |  |
| reused_from_kb_id | INTEGER |  |  |
| status_detail | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
