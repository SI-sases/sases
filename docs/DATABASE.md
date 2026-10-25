# SASES 数据库结构

共 64 张表

## agent_friendships (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| friend_agent_id | TEXT |  |  |
| status | TEXT | 'pending' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| target_user_id | INTEGER |  |  |

## ai_circle_posts (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| agent_id | TEXT |  |  |
| owner_user_id | INTEGER |  |  |
| content | TEXT |  |  |
| post_type | TEXT | 'daily' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## api_keys (3 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| provider | TEXT |  |  |
| encrypted_key | TEXT |  |  |
| priority | INTEGER | 0 |  |
| is_active | INTEGER | 1 |  |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP |  |

## attachments (68 行)
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

## base_facilities (24 行)
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

## compute_transactions (1 行)
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

## contribution_log (673 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| event_type | TEXT |  |  |
| target_id | TEXT |  |  |
| metadata | TEXT |  |  |
| timestamp | TIMESTAMP | CURRENT_TIMESTAMP |  |
| action | TEXT |  |  |
| model_source | TEXT |  |  |
| model_id | TEXT |  |  |
| detail | TEXT |  |  |
| points | REAL | 0 |  |
| created_at | TEXT | NULL |  |
| context_type | TEXT | 'personal' |  |
| group_id | INTEGER |  |  |
| role | TEXT |  |  |

## conversations (10 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| title | TEXT | '新会话' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |
| unread_count | INTEGER | 0 |  |
| is_pinned | INTEGER | 0 |  |
| mode | TEXT | 'normal' |  |

## credit_ledger (46 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| amount | INTEGER |  |  |
| reason | TEXT |  |  |
| timestamp | TIMESTAMP | CURRENT_TIMESTAMP |  |

## credit_pool (13 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| amount | REAL |  |  |
| source | TEXT |  |  |
| created_at | TEXT |  |  |

## domains (5 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| domain | TEXT |  | 是 |
| pattern_count | INTEGER | 0 |  |
| active | INTEGER | 0 |  |
| activated_at | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## execution_notes (1195 行)
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

## external_seed_pool (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | TEXT |  | 是 |
| description | TEXT |  |  |
| test_cases | TEXT |  |  |
| source | TEXT | 'external_api' |  |
| user_id | TEXT |  |  |
| timestamp | TEXT |  |  |

## failed_cases (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_id | INTEGER |  |  |
| issue_id | INTEGER |  |  |
| original_title | TEXT |  |  |
| original_detail | TEXT |  |  |
| failed_solution | TEXT |  |  |
| failure_reason | TEXT |  |  |
| attempts | INTEGER | 1 |  |
| status | TEXT | 'pending' |  |
| seed_generated | INTEGER | 0 |  |
| resolved_solution | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| resolved_at | TEXT |  |  |

## game_resources (16 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| owner_user_id | INTEGER |  |  |
| resource_type | TEXT |  |  |
| amount | INTEGER | 0 |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## group_airdrop_log (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| airdrop_date | TEXT |  |  |
| activity_score | REAL |  |  |
| rank | INTEGER |  |  |
| amount | REAL |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_credit_log (22 行)
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

## group_members (7 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| role | TEXT | 'member' |  |
| contribution_points | REAL | 0 |  |
| compute_contribution | REAL | 0 |  |
| execute_contribution | REAL | 0 |  |
| agent_id | TEXT |  |  |
| last_read_at | TEXT |  |  |
| origin_node | TEXT |  |  |
| user_sases_id | TEXT |  |  |
| nickname | TEXT |  |  |
| is_muted | INTEGER | 0 |  |

## group_messages (56 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| sender_id | INTEGER |  |  |
| content | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| sender_agent_id | TEXT |  |  |
| global_msg_id | TEXT |  |  |
| origin_node | TEXT |  |  |
| message_type | TEXT | 'text' |  |
| related_id | INTEGER |  |  |
| extra_data | TEXT |  |  |

## group_red_packet_claims (14 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| packet_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| amount | REAL |  |  |
| claimed_at | TEXT | CURRENT_TIMESTAMP |  |

## group_red_packets (7 行)
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
| packet_type | TEXT | "lucky" |  |

## group_report_queue (2 行)
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

## group_resource_usage (23 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| agent_id | TEXT |  |  |
| model_id | TEXT |  |  |
| tokens_used | INTEGER | 0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |

## group_stakes (5 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| group_id | INTEGER |  |  |
| user_id | INTEGER |  |  |
| amount | REAL |  |  |
| status | TEXT | 'active' |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| withdrawn_at | TEXT |  |  |

## group_task_results_global (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task_hash | TEXT |  |  |
| result_summary | TEXT |  |  |
| verified | INTEGER | 0 |  |
| valid_until | TEXT |  |  |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP |  |

## group_task_submissions (4 行)
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

## group_tasks (8 行)
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

## groups (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| name | TEXT |  |  |
| owner_id | INTEGER |  |  |
| mode | TEXT | 'normal' |  |
| settle_time | TEXT | '23:00' |  |
| decay_strength | TEXT | 'medium' |  |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP |  |
| is_pinned | INTEGER | 0 |  |
| global_group_id | TEXT |  |  |
| origin_node | TEXT |  |  |
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

## intent_feedback (4 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| task_id | TEXT |  |  |
| original_input | TEXT |  |  |
| feedback_type | TEXT | 'false_positive' |  |
| note | TEXT |  |  |
| created_at | TEXT |  |  |

## interaction_patterns (103 行)
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

## kb_entries (730 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | TEXT |  | 是 |
| task | TEXT |  |  |
| branch_a | TEXT |  |  |
| branch_b | TEXT |  |  |
| solution | TEXT |  |  |
| verified | INTEGER | 0 |  |
| model_id | TEXT |  |  |
| user_id | TEXT |  |  |
| timestamp | TEXT |  |  |
| backtrack_count | INTEGER | 0 |  |
| test_cases | TEXT |  |  |

## knowledge_base (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| task | TEXT |  |  |
| branch_a | TEXT |  |  |
| branch_b | TEXT |  |  |
| solution | TEXT |  |  |
| verified | INTEGER | 0 |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| source_task_id | INTEGER |  |  |
| source_type | TEXT | 'seed' |  |
| contributor_id | INTEGER |  |  |
| hit_count | INTEGER | 0 |  |
| solution_hash | TEXT |  |  |
| issue_id | INTEGER |  |  |
| last_reused_at | TEXT |  |  |
| quality_score | INTEGER | 0 |  |
| last_used_at | TEXT |  |  |

## knowledge_docs (18 行)
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

## main_seed_pool (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | TEXT |  | 是 |
| description | TEXT |  |  |
| test_cases | TEXT |  |  |
| source | TEXT | 'external_api' |  |
| user_id | TEXT |  |  |
| timestamp | TEXT |  |  |

## market_orders (1 行)
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

## messages (10207 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| conversation_id | INTEGER |  |  |
| sender | TEXT |  |  |
| content | TEXT |  |  |
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| sender_agent_id | TEXT |  |  |

## model_configs (6 行)
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

## pets (7 行)
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

## project_docs (69 行)
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

## project_docs_meta (12 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| source_file | TEXT |  | 是 |
| source_version | TEXT |  |  |
| chunk_count | INTEGER | 0 |  |
| file_hash | TEXT |  |  |
| imported_at | TEXT |  |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## quality_issues (9 行)
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

## rescue_tasks (8 行)
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
| created_at | TEXT | CURRENT_TIMESTAMP |  |
| assigned_agent_id | TEXT |  |  |
| solution | TEXT |  |  |
| verification_result | TEXT |  |  |
| attempts | INTEGER | 0 |  |
| status_detail | TEXT |  |  |
| reuse_count | INTEGER | 0 |  |
| cached_solution_id | INTEGER |  |  |
| reused_from_kb_id | INTEGER |  |  |

## safety_log (1713 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| timestamp | TEXT |  |  |
| content_preview | TEXT |  |  |
| category | TEXT |  |  |
| detail | TEXT |  |  |

## safety_memory (1785 行)
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

## shared_pollinate_log (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| kb_id | TEXT |  | 是 |
| timestamp | TEXT |  |  |

## space_nodes (4 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| node_id | TEXT |  | 是 |
| name | TEXT |  |  |
| description | TEXT |  |  |
| node_type | TEXT |  |  |
| capabilities | TEXT |  |  |
| endpoint | TEXT |  |  |
| icon | TEXT |  |  |
| owner_id | TEXT |  |  |
| registered_at | TEXT |  |  |
| reputation | REAL | 1.0 |  |
| success_count | INTEGER | 0 |  |
| total_count | INTEGER | 0 |  |
| status | TEXT | 'unknown' |  |

## supervisor_runs (310 行)
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

## swarm_pending_tasks (21 行)
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
| supervisor_id | TEXT |  |  |
| supervisor_run_id | INTEGER |  |  |

## swarm_reviews (4122 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
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
| step_type | TEXT |  |  |

## system_messages (99 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| title | TEXT | 'SASES助手' |  |
| content | TEXT |  |  |
| is_read | INTEGER | 0 |  |
| timestamp | TIMESTAMP | CURRENT_TIMESTAMP |  |

## tamper_log (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| user_id | INTEGER |  |  |
| detail | TEXT |  |  |
| timestamp | TEXT |  |  |

## transactions (3 行)
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

## user_compute_balance (1 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| balance | INTEGER | 0 |  |
| total_purchased | INTEGER | 0 |  |
| total_consumed | INTEGER | 0 |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## user_settings (0 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| key | TEXT |  | 是 |
| value | TEXT |  |  |

## users (8 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| id | INTEGER |  | 是 |
| username | TEXT |  |  |
| email | TEXT |  |  |
| password_hash | TEXT |  |  |
| credits | INTEGER | 0 |  |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP |  |
| state_hash | TEXT | '' |  |
| tampered_flag | INTEGER | 0 |  |
| auto_pollinate_enabled | INTEGER | 1 |  |
| is_admin | INTEGER | 0 |  |
| sases_id | TEXT |  |  |
| gender | TEXT |  |  |
| region | TEXT |  |  |
| signature | TEXT |  |  |
| onboarding_day | INTEGER | 1 |  |
| onboarding_completed | TEXT | '[]' |  |
| onboarding_started_at | TEXT |  |  |

## work_logs (41 行)
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

## yunchong_official_agent_usage (1 行)
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

## yunchong_refresh_log (2 行)
| 字段 | 类型 | 默认 | 主键 |
|------|------|------|------|
| user_id | INTEGER |  | 是 |
| last_refresh_at | TEXT |  |  |
| current_batch_id | TEXT |  |  |
| updated_at | TEXT | CURRENT_TIMESTAMP |  |

## yunchong_tasks (299 行)
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
