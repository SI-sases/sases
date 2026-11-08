# Schema 差异清单

## 行数统计

- reference vs Node-A: 827 行
- reference vs Node-B: 789 行
- Node-A vs Node-B: 61 行

## reference vs Node-A

```
--- reference
+++ Node-A
@@ -0,0 +1,824 @@
+CREATE TABLE users (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                username TEXT UNIQUE NOT NULL,
+                password_hash TEXT NOT NULL,
+                sases_id TEXT,
+                credits REAL DEFAULT 0,
+                gender TEXT,
+                region TEXT,
+                signature TEXT,
+                onboarding_day INTEGER DEFAULT 1,
+                onboarding_completed TEXT DEFAULT '[]',
+                onboarding_started_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , state_hash TEXT, tampered_flag INTEGER DEFAULT 0, auto_pollinate_enabled INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0, email TEXT, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', handle TEXT, display_name TEXT, last_pulled_id INTEGER DEFAULT 0, last_pulled_group_id INTEGER DEFAULT 0)
+CREATE TABLE sqlite_sequence(name,seq)
+CREATE TABLE node_registry (
+                node_id TEXT PRIMARY KEY,
+                public_key TEXT,
+                url TEXT,
+                role TEXT,
+                status TEXT DEFAULT 'active',
+                first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
+                last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
+                master_epoch INTEGER DEFAULT 0,
+                priority INTEGER DEFAULT 100
+            )
+CREATE TABLE api_keys (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                provider TEXT NOT NULL,
+                api_key_encrypted TEXT NOT NULL,
+                priority INTEGER DEFAULT 1,
+                is_active INTEGER DEFAULT 1,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE knowledge_base (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task TEXT NOT NULL,
+                branch_a TEXT,
+                branch_b TEXT,
+                solution TEXT NOT NULL,
+                verified INTEGER DEFAULT 0,
+                source_task_id INTEGER,
+                contributor_id INTEGER,
+                hit_count INTEGER DEFAULT 0,
+                quality_score INTEGER DEFAULT 0,
+                last_used_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE TABLE contribution_log (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                action TEXT,
+                event_type TEXT DEFAULT 'manual',
+                points REAL DEFAULT 0,
+                model_source TEXT DEFAULT 'api',
+                model_id TEXT,
+                detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, origin_node TEXT DEFAULT 'node-A', logical_clock INTEGER DEFAULT 0,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE model_configs (
+                id TEXT PRIMARY KEY,
+                user_id INTEGER NOT NULL,
+                model_type TEXT NOT NULL,
+                name TEXT NOT NULL,
+                provider TEXT,
+                api_key_encrypted TEXT,
+                node_url TEXT,
+                model_name TEXT,
+                capabilities TEXT,
+                is_shared INTEGER DEFAULT 0,
+                visibility TEXT DEFAULT 'private',
+                price REAL DEFAULT 1.0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE conversations (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                agent_id TEXT,
+                title TEXT DEFAULT '新会话',
+                mode TEXT DEFAULT 'normal',
+                unread_count INTEGER DEFAULT 0,
+                is_pinned INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', target_user_id INTEGER, is_friend_chat INTEGER DEFAULT 0, friend_mode TEXT DEFAULT 'normal',
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE messages (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                conversation_id INTEGER NOT NULL,
+                sender TEXT NOT NULL,
+                content TEXT NOT NULL,
+                sender_agent_id TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', msg_type TEXT, attachments TEXT,
+                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
+            )
+CREATE TABLE agent_friendships (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                friend_agent_id TEXT NOT NULL,
+                target_user_id INTEGER,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, friend_mode TEXT DEFAULT 'normal', auth_token TEXT,
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (target_user_id) REFERENCES users(id)
+            )
+CREATE TABLE groups (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                name TEXT NOT NULL,
+                owner_id INTEGER NOT NULL,
+                mode TEXT DEFAULT 'normal',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, global_group_id TEXT, origin_node TEXT, is_pinned INTEGER DEFAULT 0, credits REAL DEFAULT 0, staked_credits REAL DEFAULT 0, features TEXT DEFAULT '{}', red_packet_hour INTEGER DEFAULT 20, red_packet_audience TEXT DEFAULT 'all', airdrop_enabled INTEGER DEFAULT 1, airdrop_paused_until TEXT, last_red_packet_date TEXT, pool_packet_amount REAL DEFAULT 0, pool_packet_count INTEGER DEFAULT 5, announcement TEXT, logical_clock INTEGER DEFAULT 0, hlc_ts TEXT, shard_key TEXT DEFAULT '',
+                FOREIGN KEY (owner_id) REFERENCES users(id)
+            )
+CREATE TABLE group_members (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER,
+                agent_id TEXT,
+                role TEXT DEFAULT 'member',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, last_read_at TEXT, origin_node TEXT, user_sases_id TEXT, nickname TEXT, is_muted INTEGER DEFAULT 0, hlc_ts TEXT, shard_key TEXT DEFAULT '',
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE group_messages (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                sender_id INTEGER,
+                sender_agent_id TEXT,
+                content TEXT NOT NULL,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, global_msg_id TEXT, origin_node TEXT, message_type TEXT DEFAULT 'text', related_id INTEGER, extra_data TEXT, logical_clock INTEGER DEFAULT 0, hlc_ts TEXT, shard_key TEXT DEFAULT '', msg_type TEXT DEFAULT 'standard', attachments TEXT,
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (sender_id) REFERENCES users(id)
+            )
+CREATE TABLE group_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                global_task_id TEXT,
+                title TEXT NOT NULL,
+                description TEXT,
+                task_category TEXT DEFAULT 'text',
+                created_by INTEGER NOT NULL,
+                reward_credits REAL NOT NULL DEFAULT 0,
+                status TEXT DEFAULT 'open',
+                selected_submission_id INTEGER,
+                judging_deadline TEXT,
+                reject_reason TEXT,
+                last_repushed_at TEXT,
+                repush_count INTEGER DEFAULT 0,
+                origin_node TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (created_by) REFERENCES users(id)
+            )
+CREATE TABLE group_task_submissions (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id INTEGER NOT NULL,
+                global_submission_id TEXT,
+                submitted_by INTEGER NOT NULL,
+                agent_id TEXT,
+                content TEXT NOT NULL,
+                content_type TEXT DEFAULT 'text',
+                is_disqualified INTEGER DEFAULT 0,
+                edited_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (task_id) REFERENCES group_tasks(id),
+                FOREIGN KEY (submitted_by) REFERENCES users(id)
+            )
+CREATE TABLE group_credit_log (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER,
+                amount REAL NOT NULL,
+                tx_type TEXT NOT NULL,
+                detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE group_stakes (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER NOT NULL,
+                amount REAL NOT NULL,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                withdrawn_at TEXT,
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE group_airdrop_log (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                airdrop_date TEXT NOT NULL,
+                activity_score REAL NOT NULL,
+                rank INTEGER,
+                amount REAL NOT NULL,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE UNIQUE INDEX idx_airdrop_group_date
+            ON group_airdrop_log(group_id, airdrop_date)
+        
+CREATE TABLE knowledge_docs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                scope TEXT NOT NULL DEFAULT 'group',
+                group_id INTEGER,
+                title TEXT,
+                content TEXT NOT NULL,
+                category TEXT DEFAULT 'doc',
+                tags TEXT,
+                source_type TEXT DEFAULT 'manual',
+                source_id TEXT,
+                contributor_id INTEGER,
+                hit_count INTEGER DEFAULT 0,
+                visibility TEXT DEFAULT 'group',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT
+            )
+CREATE INDEX idx_kdocs_scope_group ON knowledge_docs(scope, group_id)
+CREATE INDEX idx_kdocs_category ON knowledge_docs(category)
+CREATE TABLE group_report_queue (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                question TEXT NOT NULL,
+                asked_by INTEGER,
+                anonymous INTEGER DEFAULT 0,
+                hit_knowledge_id INTEGER,
+                status TEXT DEFAULT 'pending',
+                resolved_kb_id INTEGER,
+                resolved_by INTEGER,
+                resolved_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_grq_group_status ON group_report_queue(group_id, status)
+CREATE TABLE group_resource_pool (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                agent_id TEXT NOT NULL,
+                model_id TEXT,
+                daily_limit INTEGER DEFAULT 100,
+                enabled INTEGER DEFAULT 1,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE UNIQUE INDEX idx_grp_pool_agent ON group_resource_pool(group_id, agent_id)
+CREATE INDEX idx_grp_pool_model ON group_resource_pool(model_id)
+CREATE TABLE group_invite_pending (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                inviter_id INTEGER NOT NULL,
+                invitee TEXT NOT NULL,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                resolved_at TEXT,
+                resolved_by INTEGER
+            )
+CREATE INDEX idx_grp_invite_status ON group_invite_pending(group_id, status)
+CREATE TABLE group_resource_usage (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER NOT NULL,
+                agent_id TEXT,
+                model_id TEXT,
+                tokens_used INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_grp_usage_date ON group_resource_usage(group_id, user_id, created_at)
+CREATE TABLE group_red_packets (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                sender_id INTEGER NOT NULL,
+                source_type TEXT DEFAULT 'user',
+                total_amount REAL NOT NULL,
+                total_count INTEGER NOT NULL,
+                claimed_count INTEGER DEFAULT 0,
+                remaining_amount REAL NOT NULL,
+                message TEXT,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                expires_at TEXT
+            )
+CREATE INDEX idx_grp_rp_group ON group_red_packets(group_id, status)
+CREATE INDEX idx_grp_rp_expires ON group_red_packets(status, expires_at)
+CREATE TABLE group_red_packet_claims (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                packet_id INTEGER NOT NULL,
+                user_id INTEGER NOT NULL,
+                amount REAL NOT NULL,
+                claimed_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE UNIQUE INDEX idx_grp_rpc_pid_uid ON group_red_packet_claims(packet_id, user_id)
+CREATE TABLE market_orders (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                order_type TEXT NOT NULL,
+                description TEXT NOT NULL,
+                price REAL NOT NULL,
+                status TEXT DEFAULT 'open',
+                accepted_by INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (accepted_by) REFERENCES users(id)
+            )
+CREATE TABLE ai_circle_posts (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                agent_id TEXT NOT NULL,
+                owner_user_id INTEGER NOT NULL,
+                content TEXT NOT NULL,
+                post_type TEXT DEFAULT 'daily',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE transactions (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                sender_id INTEGER NOT NULL,
+                receiver_id INTEGER NOT NULL,
+                amount REAL NOT NULL,
+                tx_type TEXT NOT NULL,
+                status TEXT DEFAULT 'pending',
+                message TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                completed_at TEXT,
+                expires_at TEXT,
+                claimed_at TEXT, origin_node TEXT DEFAULT 'node-A', logical_clock INTEGER DEFAULT 0, idempotency_key TEXT, sender_node_id TEXT, receiver_node_id TEXT, credit_type TEXT DEFAULT 'credits',
+                FOREIGN KEY (sender_id) REFERENCES users(id),
+                FOREIGN KEY (receiver_id) REFERENCES users(id)
+            )
+CREATE TABLE ledger_versions (
+                node_id TEXT PRIMARY KEY,
+                version INTEGER DEFAULT 0,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE forwarded_requests (
+                request_id TEXT PRIMARY KEY,
+                node_id TEXT,
+                result_json TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE space_nodes (
+                node_id TEXT PRIMARY KEY,
+                name TEXT,
+                description TEXT,
+                node_type TEXT DEFAULT 'harness',
+                capabilities TEXT,
+                endpoint TEXT,
+                icon TEXT,
+                owner_id TEXT DEFAULT 'system',
+                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                reputation REAL DEFAULT 1.0,
+                success_count INTEGER DEFAULT 0,
+                total_count INTEGER DEFAULT 0,
+                status TEXT DEFAULT 'unknown'
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE TABLE credit_anchors (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                node_id TEXT NOT NULL,
+                ts TEXT NOT NULL,
+                anchor_hash TEXT NOT NULL,
+                record_count INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_credit_anchors_node_ts ON credit_anchors(node_id, ts)
+CREATE TABLE seed_tasks (
+                id TEXT PRIMARY KEY,
+                description TEXT NOT NULL,
+                domain TEXT,
+                difficulty TEXT DEFAULT 'medium',
+                user_id INTEGER,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE safety_memory (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                memory_type TEXT NOT NULL,
+                content TEXT NOT NULL,
+                full_data TEXT,
+                agent_id TEXT,
+                user_id INTEGER NOT NULL,
+                group_id INTEGER,
+                importance REAL DEFAULT 0.5,
+                tags TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                expires_at TEXT, task_id TEXT, embedding BLOB, content_hash TEXT, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '',
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (group_id) REFERENCES groups(id)
+            )
+CREATE TABLE work_logs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                agent_id TEXT,
+                command TEXT NOT NULL,
+                output TEXT,
+                status TEXT DEFAULT 'success',
+                duration_ms INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE quality_issues (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                source TEXT NOT NULL,
+                source_id TEXT,
+                title TEXT NOT NULL,
+                detail TEXT,
+                severity TEXT DEFAULT 'low',
+                status TEXT DEFAULT 'pending',
+                user_id INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                cleaned_at TEXT,
+                assigned_to TEXT,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE rescue_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                issue_id INTEGER NOT NULL,
+                difficulty TEXT DEFAULT 'medium',
+                pet_level TEXT DEFAULT 'C',
+                status TEXT DEFAULT 'available',
+                rescued_by_user_id INTEGER,
+                rescued_by_agent_id TEXT,
+                rescued_at TEXT,
+                assigned_agent_id TEXT,
+                solution TEXT,
+                verification_result TEXT,
+                attempts INTEGER DEFAULT 0,
+                status_detail TEXT,
+                reused_from_kb_id INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (issue_id) REFERENCES quality_issues(id),
+                FOREIGN KEY (rescued_by_user_id) REFERENCES users(id)
+            )
+CREATE TABLE yunchong_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                issue_id INTEGER,
+                title TEXT NOT NULL,
+                detail TEXT,
+                difficulty TEXT DEFAULT 'medium',
+                pet_level TEXT DEFAULT 'C',
+                status TEXT DEFAULT 'available',
+                longitude REAL DEFAULT 0,
+                latitude REAL DEFAULT 0,
+                distance_meters INTEGER DEFAULT 0,
+                energy_cost INTEGER DEFAULT 0,
+                batch_id TEXT,
+                refreshed_at TEXT,
+                expires_at TEXT,
+                rescued_at TEXT,
+                rescued_by_agent_id TEXT,
+                solution TEXT,
+                verification_result TEXT,
+                attempts INTEGER DEFAULT 0,
+                reused_from_kb_id INTEGER,
+                status_detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (owner_user_id) REFERENCES users(id),
+                FOREIGN KEY (issue_id) REFERENCES quality_issues(id)
+            )
+CREATE TABLE yunchong_refresh_log (
+                user_id INTEGER PRIMARY KEY,
+                last_refresh_at TEXT,
+                current_batch_id TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE yunchong_official_agent_usage (
+                user_id INTEGER PRIMARY KEY,
+                used_today INTEGER DEFAULT 0,
+                reset_date TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE yunchong_radar (
+                user_id INTEGER PRIMARY KEY,
+                expires_at TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE failed_cases (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id INTEGER,
+                issue_id INTEGER,
+                title TEXT,
+                detail TEXT,
+                solution TEXT,
+                fail_reason TEXT,
+                verification_result TEXT,
+                severity TEXT,
+                seed_triggered INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE pets (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                pet_name TEXT,
+                rarity TEXT NOT NULL,
+                camp TEXT NOT NULL,
+                element TEXT NOT NULL,
+                level INTEGER DEFAULT 1,
+                exp INTEGER DEFAULT 0,
+                stage INTEGER DEFAULT 0,
+                skill_slots INTEGER DEFAULT 1,
+                current_skills TEXT,
+                strength INTEGER DEFAULT 0,
+                hp INTEGER DEFAULT 0,
+                defense INTEGER DEFAULT 0,
+                is_listed INTEGER DEFAULT 0,
+                source_task_id INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE game_resources (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                resource_type TEXT NOT NULL,
+                amount INTEGER DEFAULT 0,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                UNIQUE(owner_user_id, resource_type),
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE base_facilities (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                facility_type TEXT NOT NULL,
+                level INTEGER DEFAULT 0,
+                captain_pet_id INTEGER,
+                member_pet_ids TEXT,
+                status TEXT DEFAULT 'idle',
+                last_produced_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                UNIQUE(owner_user_id, facility_type),
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE official_compute_services (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                service_key TEXT UNIQUE NOT NULL,
+                service_name TEXT NOT NULL,
+                description TEXT,
+                unit_cost INTEGER DEFAULT 1,
+                is_active INTEGER DEFAULT 1,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE user_compute_balance (
+                user_id INTEGER PRIMARY KEY,
+                balance INTEGER DEFAULT 0,
+                total_purchased INTEGER DEFAULT 0,
+                total_consumed INTEGER DEFAULT 0,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE compute_transactions (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                tx_type TEXT NOT NULL,
+                amount INTEGER NOT NULL,
+                balance_after INTEGER NOT NULL,
+                service_key TEXT,
+                detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE swarm_pending_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT UNIQUE NOT NULL,
+                conversation_id INTEGER,
+                user_id INTEGER NOT NULL,
+                commander_id TEXT,
+                executor_id TEXT,
+                user_text TEXT,
+                steps TEXT,
+                results TEXT,
+                done_steps TEXT,
+                retry_count INTEGER DEFAULT 0,
+                is_draft INTEGER DEFAULT 0,
+                cancelled INTEGER DEFAULT 0,
+                no_plan INTEGER DEFAULT 0,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP, supervisor_run_id INTEGER, supervisor_id TEXT,
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
+            )
+CREATE TABLE swarm_reviews (
+                step_type TEXT,  -- v0.17.0 区分 command / harness
+
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT NOT NULL,
+                conversation_id INTEGER,
+                step_id INTEGER,
+                command TEXT,
+                exec_status TEXT,
+                review_result TEXT,
+                review_reason TEXT,
+                output_preview TEXT,
+                created_at TEXT NOT NULL
+            )
+CREATE TABLE intent_feedback (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                task_id TEXT,
+                original_input TEXT NOT NULL,
+                feedback_type TEXT NOT NULL DEFAULT 'false_positive',
+                note TEXT,
+                created_at TEXT NOT NULL
+            )
+CREATE TABLE interaction_patterns (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                domain TEXT NOT NULL DEFAULT 'general',
+                pattern_key TEXT NOT NULL,
+                pattern_type TEXT NOT NULL,
+                context_signature TEXT NOT NULL,
+                role TEXT,
+                evidence TEXT,
+                confidence REAL DEFAULT 0.5,
+                hit_count INTEGER DEFAULT 0,
+                success_count INTEGER DEFAULT 0,
+                fail_count INTEGER DEFAULT 0,
+                distinct_user_count INTEGER DEFAULT 0,
+                last_hit_at TEXT,
+                last_success_at TEXT,
+                status TEXT DEFAULT 'active',
+                source_task_id TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE UNIQUE INDEX idx_patterns_key_sig ON interaction_patterns(domain, pattern_key, context_signature)
+CREATE INDEX idx_patterns_domain_type ON interaction_patterns(domain, pattern_type, status)
+CREATE INDEX idx_patterns_updated ON interaction_patterns(updated_at)
+CREATE TABLE domains (
+                domain TEXT PRIMARY KEY,
+                pattern_count INTEGER DEFAULT 0,
+                active INTEGER DEFAULT 0,
+                activated_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE project_docs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                source_file TEXT NOT NULL,
+                section_title TEXT,
+                section_path TEXT,
+                section_level INTEGER DEFAULT 2,
+                chunk_index INTEGER DEFAULT 0,
+                content TEXT NOT NULL,
+                embedding BLOB,
+                content_hash TEXT,
+                freshness_score REAL DEFAULT 1.0,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , user_id INTEGER DEFAULT 0, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE INDEX idx_pdocs_source ON project_docs(source_file)
+CREATE INDEX idx_pdocs_hash ON project_docs(content_hash)
+CREATE INDEX idx_pdocs_status ON project_docs(status)
+CREATE TABLE project_docs_meta (
+                source_file TEXT PRIMARY KEY,
+                source_version TEXT,
+                chunk_count INTEGER DEFAULT 0,
+                file_hash TEXT,
+                imported_at TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE execution_notes (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT,
+                user_id INTEGER,
+                user_input TEXT NOT NULL,
+                summary TEXT,
+                outcome TEXT DEFAULT 'success',
+                steps_digest TEXT,
+                embedding BLOB,
+                content_hash TEXT,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_exnotes_hash ON execution_notes(content_hash)
+CREATE INDEX idx_exnotes_task ON execution_notes(task_id)
+CREATE INDEX idx_exnotes_status ON execution_notes(status)
+CREATE TABLE attachments (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                file_id TEXT UNIQUE NOT NULL,
+                user_id INTEGER NOT NULL,
+                original_name TEXT,
+                stored_path TEXT NOT NULL,
+                mime_type TEXT,
+                size_bytes INTEGER DEFAULT 0,
+                kind TEXT DEFAULT 'file',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE INDEX idx_attach_user ON attachments(user_id)
+CREATE INDEX idx_attach_fileid ON attachments(file_id)
+CREATE TABLE supervisor_runs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                conversation_id INTEGER NOT NULL,
+                supervisor_id TEXT,
+                goal TEXT NOT NULL,
+                status TEXT DEFAULT 'running',
+                current_round INTEGER DEFAULT 0,
+                max_rounds INTEGER DEFAULT 5,
+                credits_used INTEGER DEFAULT 0,
+                history TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                finished_at TEXT
+            , task_type TEXT)
+CREATE INDEX idx_suprun_user ON supervisor_runs(user_id)
+CREATE TABLE credit_pool (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                amount REAL NOT NULL,
+                source TEXT,
+                created_at TEXT
+            )
+CREATE INDEX idx_credit_pool_time ON credit_pool(created_at)
+CREATE INDEX idx_yunchong_owner_status ON yunchong_tasks(owner_user_id, status)
+CREATE INDEX idx_yunchong_batch ON yunchong_tasks(batch_id)
+CREATE INDEX idx_yunchong_expires ON yunchong_tasks(expires_at)
+CREATE INDEX idx_memory_task ON safety_memory(task_id)
+CREATE INDEX idx_memory_hash ON safety_memory(content_hash)
+CREATE INDEX idx_memory_user_type ON safety_memory(user_id, memory_type)
+CREATE INDEX idx_swarm_pending_task ON swarm_pending_tasks(task_id)
+CREATE INDEX idx_swarm_pending_status ON swarm_pending_tasks(status)
+CREATE INDEX idx_swarm_pending_conv ON swarm_pending_tasks(conversation_id)
+CREATE INDEX idx_swarm_reviews_task ON swarm_reviews(task_id)
+CREATE INDEX idx_swarm_reviews_time ON swarm_reviews(created_at)
+CREATE INDEX idx_swarm_reviews_conversation ON swarm_reviews(conversation_id)
+CREATE TABLE task_feedback (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT NOT NULL,
+                user_id INTEGER NOT NULL,
+                conversation_id INTEGER,
+                task_source TEXT NOT NULL,
+                feedback_type TEXT NOT NULL,
+                rating TEXT,
+                reason_tag TEXT,
+                reason_text TEXT,
+                task_snapshot TEXT NOT NULL,
+                result_snapshot TEXT NOT NULL,
+                metadata TEXT,
+                weight REAL DEFAULT 1.0,
+                is_latest INTEGER DEFAULT 1,
+                task_alive INTEGER DEFAULT 1,
+                created_at TEXT NOT NULL,
+                updated_at TEXT
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE INDEX idx_feedback_task ON task_feedback(task_id)
+CREATE INDEX idx_feedback_user ON task_feedback(user_id, created_at)
+CREATE INDEX idx_feedback_rating ON task_feedback(rating, created_at)
+CREATE INDEX idx_feedback_reason ON task_feedback(reason_tag)
+CREATE INDEX idx_conversations_hlc ON conversations(hlc_ts)
+CREATE INDEX idx_conversations_shard ON conversations(shard_key)
+CREATE INDEX idx_group_members_hlc ON group_members(hlc_ts)
+CREATE INDEX idx_group_members_shard ON group_members(shard_key)
+CREATE INDEX idx_group_messages_hlc ON group_messages(hlc_ts)
+CREATE INDEX idx_group_messages_shard ON group_messages(shard_key)
+CREATE INDEX idx_groups_hlc ON groups(hlc_ts)
+CREATE INDEX idx_groups_shard ON groups(shard_key)
+CREATE INDEX idx_interaction_patterns_hlc ON interaction_patterns(hlc_ts)
+CREATE INDEX idx_interaction_patterns_shard ON interaction_patterns(shard_key)
+CREATE INDEX idx_knowledge_base_hlc ON knowledge_base(hlc_ts)
+CREATE INDEX idx_knowledge_base_shard ON knowledge_base(shard_key)
+CREATE INDEX idx_messages_hlc ON messages(hlc_ts)
+CREATE INDEX idx_messages_shard ON messages(shard_key)
+CREATE INDEX idx_project_docs_hlc ON project_docs(hlc_ts)
+CREATE INDEX idx_project_docs_shard ON project_docs(shard_key)
+CREATE INDEX idx_safety_memory_hlc ON safety_memory(hlc_ts)
+CREATE INDEX idx_safety_memory_shard ON safety_memory(shard_key)
+CREATE INDEX idx_space_nodes_hlc ON space_nodes(hlc_ts)
+CREATE INDEX idx_space_nodes_shard ON space_nodes(shard_key)
+CREATE INDEX idx_task_feedback_hlc ON task_feedback(hlc_ts)
+CREATE INDEX idx_task_feedback_shard ON task_feedback(shard_key)
+CREATE INDEX idx_users_hlc ON users(hlc_ts)
+CREATE INDEX idx_users_shard ON users(shard_key)
+CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)
+CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT UNIQUE NOT NULL, target_url TEXT NOT NULL, payload TEXT NOT NULL, headers TEXT, status TEXT NOT NULL DEFAULT 'pending', retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 5, next_retry_at TEXT NOT NULL, last_error TEXT, created_at TEXT NOT NULL, completed_at TEXT)
+CREATE INDEX idx_outbox_due ON outbox(status, next_retry_at)
+CREATE INDEX idx_outbox_msg ON outbox(msg_id)
+CREATE TABLE auth_meta (key TEXT PRIMARY KEY, value TEXT)
+CREATE TABLE nonce_cache (user_id INTEGER, nonce TEXT, expire_at TEXT, PRIMARY KEY (user_id, nonce))
+CREATE TABLE asset_snapshots (snapshot_date TEXT PRIMARY KEY, total_seed REAL NOT NULL, total_compute REAL NOT NULL, user_count INTEGER NOT NULL, tx_count INTEGER NOT NULL, ledger_hash TEXT NOT NULL, created_at TEXT NOT NULL)
+CREATE TABLE reconcile_issues (id INTEGER PRIMARY KEY AUTOINCREMENT, issue_type TEXT NOT NULL, detail TEXT, detected_at TEXT NOT NULL, resolved INTEGER DEFAULT 0, resolved_at TEXT, resolved_by TEXT)
+CREATE TABLE user_frozen (user_id INTEGER PRIMARY KEY, reason TEXT, frozen_at TEXT, frozen_by TEXT DEFAULT 'system')
+CREATE UNIQUE INDEX idx_transactions_idem ON transactions(idempotency_key) WHERE idempotency_key IS NOT NULL
+CREATE TABLE sync_received (idempotency_key TEXT PRIMARY KEY, received_at TEXT NOT NULL)
+CREATE TABLE api_registry (
+                api_id TEXT PRIMARY KEY,
+                endpoint TEXT NOT NULL,
+                description TEXT NOT NULL,
+                params_schema TEXT,
+                capability_tags TEXT,
+                provider_signature TEXT,
+                created_at TEXT NOT NULL
+            )
+CREATE TABLE nodes (
+            node_id TEXT PRIMARY KEY,
+            node_name TEXT,
+            role_type TEXT DEFAULT 'app_node',
+            public_key TEXT,
+            capabilities TEXT,
+            status TEXT DEFAULT 'offline',
+            last_heartbeat TEXT,
+            created_at TEXT NOT NULL
+        )
+CREATE TABLE cognitive_rules (
+            rule_id TEXT PRIMARY KEY,
+            domain_main TEXT NOT NULL,
+            domain_sub TEXT,
+            rule_content TEXT NOT NULL,
+            trigger_context TEXT,
+            confidence REAL DEFAULT 0.5,
+            applied_count INTEGER DEFAULT 0,
+            success_count INTEGER DEFAULT 0,
+            status TEXT DEFAULT 'active',
+            source_pattern_ids TEXT,
+            created_at TEXT NOT NULL,
+            updated_at TEXT
+        )
+CREATE TABLE rule_tool_bindings (
+            binding_id INTEGER PRIMARY KEY AUTOINCREMENT,
+            rule_id TEXT NOT NULL,
+            tool_id TEXT NOT NULL,
+            usage_context TEXT,
+            priority INTEGER DEFAULT 0,
+            FOREIGN KEY(rule_id) REFERENCES cognitive_rules(rule_id)
+        )
```

## reference vs Node-B

```
--- reference
+++ Node-B
@@ -0,0 +1,786 @@
+CREATE TABLE users (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                username TEXT UNIQUE NOT NULL,
+                password_hash TEXT NOT NULL,
+                sases_id TEXT,
+                credits REAL DEFAULT 0,
+                gender TEXT,
+                region TEXT,
+                signature TEXT,
+                onboarding_day INTEGER DEFAULT 1,
+                onboarding_completed TEXT DEFAULT '[]',
+                onboarding_started_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , state_hash TEXT, tampered_flag INTEGER DEFAULT 0, auto_pollinate_enabled INTEGER DEFAULT 1, is_admin INTEGER DEFAULT 0, email TEXT, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', handle TEXT, display_name TEXT, last_pulled_id INTEGER DEFAULT 0, last_pulled_group_id INTEGER DEFAULT 0)
+CREATE TABLE sqlite_sequence(name,seq)
+CREATE TABLE node_registry (
+                node_id TEXT PRIMARY KEY,
+                public_key TEXT,
+                url TEXT,
+                role TEXT,
+                status TEXT DEFAULT 'active',
+                first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
+                last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
+                master_epoch INTEGER DEFAULT 0,
+                priority INTEGER DEFAULT 100
+            )
+CREATE TABLE api_keys (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                provider TEXT NOT NULL,
+                api_key_encrypted TEXT NOT NULL,
+                priority INTEGER DEFAULT 1,
+                is_active INTEGER DEFAULT 1,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE knowledge_base (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task TEXT NOT NULL,
+                branch_a TEXT,
+                branch_b TEXT,
+                solution TEXT NOT NULL,
+                verified INTEGER DEFAULT 0,
+                source_task_id INTEGER,
+                contributor_id INTEGER,
+                hit_count INTEGER DEFAULT 0,
+                quality_score INTEGER DEFAULT 0,
+                last_used_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE TABLE contribution_log (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                action TEXT,
+                event_type TEXT DEFAULT 'manual',
+                points REAL DEFAULT 0,
+                model_source TEXT DEFAULT 'api',
+                model_id TEXT,
+                detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, origin_node TEXT DEFAULT 'node-A', logical_clock INTEGER DEFAULT 0,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE model_configs (
+                id TEXT PRIMARY KEY,
+                user_id INTEGER NOT NULL,
+                model_type TEXT NOT NULL,
+                name TEXT NOT NULL,
+                provider TEXT,
+                api_key_encrypted TEXT,
+                node_url TEXT,
+                model_name TEXT,
+                capabilities TEXT,
+                is_shared INTEGER DEFAULT 0,
+                visibility TEXT DEFAULT 'private',
+                price REAL DEFAULT 1.0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE conversations (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                agent_id TEXT,
+                title TEXT DEFAULT '新会话',
+                mode TEXT DEFAULT 'normal',
+                unread_count INTEGER DEFAULT 0,
+                is_pinned INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', target_user_id INTEGER, is_friend_chat INTEGER DEFAULT 0, friend_mode TEXT DEFAULT 'normal',
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE messages (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                conversation_id INTEGER NOT NULL,
+                sender TEXT NOT NULL,
+                content TEXT NOT NULL,
+                sender_agent_id TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', msg_type TEXT DEFAULT 'standard', attachments TEXT,
+                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
+            )
+CREATE TABLE agent_friendships (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                friend_agent_id TEXT NOT NULL,
+                target_user_id INTEGER,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, friend_mode TEXT DEFAULT 'normal', auth_token TEXT,
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (target_user_id) REFERENCES users(id)
+            )
+CREATE TABLE groups (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                name TEXT NOT NULL,
+                owner_id INTEGER NOT NULL,
+                mode TEXT DEFAULT 'normal',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, global_group_id TEXT, origin_node TEXT, is_pinned INTEGER DEFAULT 0, credits REAL DEFAULT 0, staked_credits REAL DEFAULT 0, features TEXT DEFAULT '{}', red_packet_hour INTEGER DEFAULT 20, red_packet_audience TEXT DEFAULT 'all', airdrop_enabled INTEGER DEFAULT 1, airdrop_paused_until TEXT, last_red_packet_date TEXT, pool_packet_amount REAL DEFAULT 0, pool_packet_count INTEGER DEFAULT 5, announcement TEXT, logical_clock INTEGER DEFAULT 0, hlc_ts TEXT, shard_key TEXT DEFAULT '',
+                FOREIGN KEY (owner_id) REFERENCES users(id)
+            )
+CREATE TABLE group_members (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER,
+                agent_id TEXT,
+                role TEXT DEFAULT 'member',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, last_read_at TEXT, origin_node TEXT, user_sases_id TEXT, nickname TEXT, is_muted INTEGER DEFAULT 0, hlc_ts TEXT, shard_key TEXT DEFAULT '',
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE group_messages (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                sender_id INTEGER,
+                sender_agent_id TEXT,
+                content TEXT NOT NULL,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, global_msg_id TEXT, origin_node TEXT, message_type TEXT DEFAULT 'text', related_id INTEGER, extra_data TEXT, logical_clock INTEGER DEFAULT 0, hlc_ts TEXT, shard_key TEXT DEFAULT '', msg_type TEXT DEFAULT 'standard', attachments TEXT,
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (sender_id) REFERENCES users(id)
+            )
+CREATE TABLE group_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                global_task_id TEXT,
+                title TEXT NOT NULL,
+                description TEXT,
+                task_category TEXT DEFAULT 'text',
+                created_by INTEGER NOT NULL,
+                reward_credits REAL NOT NULL DEFAULT 0,
+                status TEXT DEFAULT 'open',
+                selected_submission_id INTEGER,
+                judging_deadline TEXT,
+                reject_reason TEXT,
+                last_repushed_at TEXT,
+                repush_count INTEGER DEFAULT 0,
+                origin_node TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (created_by) REFERENCES users(id)
+            )
+CREATE TABLE group_task_submissions (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id INTEGER NOT NULL,
+                global_submission_id TEXT,
+                submitted_by INTEGER NOT NULL,
+                agent_id TEXT,
+                content TEXT NOT NULL,
+                content_type TEXT DEFAULT 'text',
+                is_disqualified INTEGER DEFAULT 0,
+                edited_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (task_id) REFERENCES group_tasks(id),
+                FOREIGN KEY (submitted_by) REFERENCES users(id)
+            )
+CREATE TABLE group_credit_log (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER,
+                amount REAL NOT NULL,
+                tx_type TEXT NOT NULL,
+                detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE group_stakes (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER NOT NULL,
+                amount REAL NOT NULL,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                withdrawn_at TEXT,
+                FOREIGN KEY (group_id) REFERENCES groups(id),
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE group_airdrop_log (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                airdrop_date TEXT NOT NULL,
+                activity_score REAL NOT NULL,
+                rank INTEGER,
+                amount REAL NOT NULL,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE UNIQUE INDEX idx_airdrop_group_date
+            ON group_airdrop_log(group_id, airdrop_date)
+        
+CREATE TABLE knowledge_docs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                scope TEXT NOT NULL DEFAULT 'group',
+                group_id INTEGER,
+                title TEXT,
+                content TEXT NOT NULL,
+                category TEXT DEFAULT 'doc',
+                tags TEXT,
+                source_type TEXT DEFAULT 'manual',
+                source_id TEXT,
+                contributor_id INTEGER,
+                hit_count INTEGER DEFAULT 0,
+                visibility TEXT DEFAULT 'group',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT
+            )
+CREATE INDEX idx_kdocs_scope_group ON knowledge_docs(scope, group_id)
+CREATE INDEX idx_kdocs_category ON knowledge_docs(category)
+CREATE TABLE group_report_queue (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                question TEXT NOT NULL,
+                asked_by INTEGER,
+                anonymous INTEGER DEFAULT 0,
+                hit_knowledge_id INTEGER,
+                status TEXT DEFAULT 'pending',
+                resolved_kb_id INTEGER,
+                resolved_by INTEGER,
+                resolved_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_grq_group_status ON group_report_queue(group_id, status)
+CREATE TABLE group_resource_pool (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                agent_id TEXT NOT NULL,
+                model_id TEXT,
+                daily_limit INTEGER DEFAULT 100,
+                enabled INTEGER DEFAULT 1,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE UNIQUE INDEX idx_grp_pool_agent ON group_resource_pool(group_id, agent_id)
+CREATE INDEX idx_grp_pool_model ON group_resource_pool(model_id)
+CREATE TABLE group_invite_pending (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                inviter_id INTEGER NOT NULL,
+                invitee TEXT NOT NULL,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                resolved_at TEXT,
+                resolved_by INTEGER
+            )
+CREATE INDEX idx_grp_invite_status ON group_invite_pending(group_id, status)
+CREATE TABLE group_resource_usage (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                user_id INTEGER NOT NULL,
+                agent_id TEXT,
+                model_id TEXT,
+                tokens_used INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_grp_usage_date ON group_resource_usage(group_id, user_id, created_at)
+CREATE TABLE group_red_packets (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                group_id INTEGER NOT NULL,
+                sender_id INTEGER NOT NULL,
+                source_type TEXT DEFAULT 'user',
+                total_amount REAL NOT NULL,
+                total_count INTEGER NOT NULL,
+                claimed_count INTEGER DEFAULT 0,
+                remaining_amount REAL NOT NULL,
+                message TEXT,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                expires_at TEXT
+            )
+CREATE INDEX idx_grp_rp_group ON group_red_packets(group_id, status)
+CREATE INDEX idx_grp_rp_expires ON group_red_packets(status, expires_at)
+CREATE TABLE group_red_packet_claims (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                packet_id INTEGER NOT NULL,
+                user_id INTEGER NOT NULL,
+                amount REAL NOT NULL,
+                claimed_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE UNIQUE INDEX idx_grp_rpc_pid_uid ON group_red_packet_claims(packet_id, user_id)
+CREATE TABLE market_orders (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                order_type TEXT NOT NULL,
+                description TEXT NOT NULL,
+                price REAL NOT NULL,
+                status TEXT DEFAULT 'open',
+                accepted_by INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (accepted_by) REFERENCES users(id)
+            )
+CREATE TABLE ai_circle_posts (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                agent_id TEXT NOT NULL,
+                owner_user_id INTEGER NOT NULL,
+                content TEXT NOT NULL,
+                post_type TEXT DEFAULT 'daily',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE transactions (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                sender_id INTEGER NOT NULL,
+                receiver_id INTEGER NOT NULL,
+                amount REAL NOT NULL,
+                tx_type TEXT NOT NULL,
+                status TEXT DEFAULT 'pending',
+                message TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                completed_at TEXT,
+                expires_at TEXT,
+                claimed_at TEXT, origin_node TEXT DEFAULT 'node-A', logical_clock INTEGER DEFAULT 0, idempotency_key TEXT, sender_node_id TEXT, receiver_node_id TEXT, credit_type TEXT DEFAULT 'credits',
+                FOREIGN KEY (sender_id) REFERENCES users(id),
+                FOREIGN KEY (receiver_id) REFERENCES users(id)
+            )
+CREATE TABLE ledger_versions (
+                node_id TEXT PRIMARY KEY,
+                version INTEGER DEFAULT 0,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE forwarded_requests (
+                request_id TEXT PRIMARY KEY,
+                node_id TEXT,
+                result_json TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE space_nodes (
+                node_id TEXT PRIMARY KEY,
+                name TEXT,
+                description TEXT,
+                node_type TEXT DEFAULT 'harness',
+                capabilities TEXT,
+                endpoint TEXT,
+                icon TEXT,
+                owner_id TEXT DEFAULT 'system',
+                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                reputation REAL DEFAULT 1.0,
+                success_count INTEGER DEFAULT 0,
+                total_count INTEGER DEFAULT 0,
+                status TEXT DEFAULT 'unknown'
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE TABLE credit_anchors (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                node_id TEXT NOT NULL,
+                ts TEXT NOT NULL,
+                anchor_hash TEXT NOT NULL,
+                record_count INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_credit_anchors_node_ts ON credit_anchors(node_id, ts)
+CREATE TABLE seed_tasks (
+                id TEXT PRIMARY KEY,
+                description TEXT NOT NULL,
+                domain TEXT,
+                difficulty TEXT DEFAULT 'medium',
+                user_id INTEGER,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE safety_memory (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                memory_type TEXT NOT NULL,
+                content TEXT NOT NULL,
+                full_data TEXT,
+                agent_id TEXT,
+                user_id INTEGER NOT NULL,
+                group_id INTEGER,
+                importance REAL DEFAULT 0.5,
+                tags TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                expires_at TEXT, task_id TEXT, embedding BLOB, content_hash TEXT, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '',
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (group_id) REFERENCES groups(id)
+            )
+CREATE TABLE work_logs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                agent_id TEXT,
+                command TEXT NOT NULL,
+                output TEXT,
+                status TEXT DEFAULT 'success',
+                duration_ms INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE quality_issues (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                source TEXT NOT NULL,
+                source_id TEXT,
+                title TEXT NOT NULL,
+                detail TEXT,
+                severity TEXT DEFAULT 'low',
+                status TEXT DEFAULT 'pending',
+                user_id INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                cleaned_at TEXT,
+                assigned_to TEXT,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE rescue_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                issue_id INTEGER NOT NULL,
+                difficulty TEXT DEFAULT 'medium',
+                pet_level TEXT DEFAULT 'C',
+                status TEXT DEFAULT 'available',
+                rescued_by_user_id INTEGER,
+                rescued_by_agent_id TEXT,
+                rescued_at TEXT,
+                assigned_agent_id TEXT,
+                solution TEXT,
+                verification_result TEXT,
+                attempts INTEGER DEFAULT 0,
+                status_detail TEXT,
+                reused_from_kb_id INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (issue_id) REFERENCES quality_issues(id),
+                FOREIGN KEY (rescued_by_user_id) REFERENCES users(id)
+            )
+CREATE TABLE yunchong_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                issue_id INTEGER,
+                title TEXT NOT NULL,
+                detail TEXT,
+                difficulty TEXT DEFAULT 'medium',
+                pet_level TEXT DEFAULT 'C',
+                status TEXT DEFAULT 'available',
+                longitude REAL DEFAULT 0,
+                latitude REAL DEFAULT 0,
+                distance_meters INTEGER DEFAULT 0,
+                energy_cost INTEGER DEFAULT 0,
+                batch_id TEXT,
+                refreshed_at TEXT,
+                expires_at TEXT,
+                rescued_at TEXT,
+                rescued_by_agent_id TEXT,
+                solution TEXT,
+                verification_result TEXT,
+                attempts INTEGER DEFAULT 0,
+                reused_from_kb_id INTEGER,
+                status_detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (owner_user_id) REFERENCES users(id),
+                FOREIGN KEY (issue_id) REFERENCES quality_issues(id)
+            )
+CREATE TABLE yunchong_refresh_log (
+                user_id INTEGER PRIMARY KEY,
+                last_refresh_at TEXT,
+                current_batch_id TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE yunchong_official_agent_usage (
+                user_id INTEGER PRIMARY KEY,
+                used_today INTEGER DEFAULT 0,
+                reset_date TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE yunchong_radar (
+                user_id INTEGER PRIMARY KEY,
+                expires_at TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE failed_cases (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id INTEGER,
+                issue_id INTEGER,
+                title TEXT,
+                detail TEXT,
+                solution TEXT,
+                fail_reason TEXT,
+                verification_result TEXT,
+                severity TEXT,
+                seed_triggered INTEGER DEFAULT 0,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE pets (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                pet_name TEXT,
+                rarity TEXT NOT NULL,
+                camp TEXT NOT NULL,
+                element TEXT NOT NULL,
+                level INTEGER DEFAULT 1,
+                exp INTEGER DEFAULT 0,
+                stage INTEGER DEFAULT 0,
+                skill_slots INTEGER DEFAULT 1,
+                current_skills TEXT,
+                strength INTEGER DEFAULT 0,
+                hp INTEGER DEFAULT 0,
+                defense INTEGER DEFAULT 0,
+                is_listed INTEGER DEFAULT 0,
+                source_task_id INTEGER,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE game_resources (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                resource_type TEXT NOT NULL,
+                amount INTEGER DEFAULT 0,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                UNIQUE(owner_user_id, resource_type),
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE base_facilities (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                owner_user_id INTEGER NOT NULL,
+                facility_type TEXT NOT NULL,
+                level INTEGER DEFAULT 0,
+                captain_pet_id INTEGER,
+                member_pet_ids TEXT,
+                status TEXT DEFAULT 'idle',
+                last_produced_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                UNIQUE(owner_user_id, facility_type),
+                FOREIGN KEY (owner_user_id) REFERENCES users(id)
+            )
+CREATE TABLE official_compute_services (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                service_key TEXT UNIQUE NOT NULL,
+                service_name TEXT NOT NULL,
+                description TEXT,
+                unit_cost INTEGER DEFAULT 1,
+                is_active INTEGER DEFAULT 1,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE user_compute_balance (
+                user_id INTEGER PRIMARY KEY,
+                balance INTEGER DEFAULT 0,
+                total_purchased INTEGER DEFAULT 0,
+                total_consumed INTEGER DEFAULT 0,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE compute_transactions (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                tx_type TEXT NOT NULL,
+                amount INTEGER NOT NULL,
+                balance_after INTEGER NOT NULL,
+                service_key TEXT,
+                detail TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE TABLE swarm_pending_tasks (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT UNIQUE NOT NULL,
+                conversation_id INTEGER,
+                user_id INTEGER NOT NULL,
+                commander_id TEXT,
+                executor_id TEXT,
+                user_text TEXT,
+                steps TEXT,
+                results TEXT,
+                done_steps TEXT,
+                retry_count INTEGER DEFAULT 0,
+                is_draft INTEGER DEFAULT 0,
+                cancelled INTEGER DEFAULT 0,
+                no_plan INTEGER DEFAULT 0,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP, supervisor_run_id INTEGER, supervisor_id TEXT,
+                FOREIGN KEY (user_id) REFERENCES users(id),
+                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
+            )
+CREATE TABLE swarm_reviews (
+                step_type TEXT,  -- v0.17.0 区分 command / harness
+
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT NOT NULL,
+                conversation_id INTEGER,
+                step_id INTEGER,
+                command TEXT,
+                exec_status TEXT,
+                review_result TEXT,
+                review_reason TEXT,
+                output_preview TEXT,
+                created_at TEXT NOT NULL
+            )
+CREATE TABLE intent_feedback (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                task_id TEXT,
+                original_input TEXT NOT NULL,
+                feedback_type TEXT NOT NULL DEFAULT 'false_positive',
+                note TEXT,
+                created_at TEXT NOT NULL
+            )
+CREATE TABLE interaction_patterns (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                domain TEXT NOT NULL DEFAULT 'general',
+                pattern_key TEXT NOT NULL,
+                pattern_type TEXT NOT NULL,
+                context_signature TEXT NOT NULL,
+                role TEXT,
+                evidence TEXT,
+                confidence REAL DEFAULT 0.5,
+                hit_count INTEGER DEFAULT 0,
+                success_count INTEGER DEFAULT 0,
+                fail_count INTEGER DEFAULT 0,
+                distinct_user_count INTEGER DEFAULT 0,
+                last_hit_at TEXT,
+                last_success_at TEXT,
+                status TEXT DEFAULT 'active',
+                source_task_id TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE UNIQUE INDEX idx_patterns_key_sig ON interaction_patterns(domain, pattern_key, context_signature)
+CREATE INDEX idx_patterns_domain_type ON interaction_patterns(domain, pattern_type, status)
+CREATE INDEX idx_patterns_updated ON interaction_patterns(updated_at)
+CREATE TABLE domains (
+                domain TEXT PRIMARY KEY,
+                pattern_count INTEGER DEFAULT 0,
+                active INTEGER DEFAULT 0,
+                activated_at TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE project_docs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                source_file TEXT NOT NULL,
+                section_title TEXT,
+                section_path TEXT,
+                section_level INTEGER DEFAULT 2,
+                chunk_index INTEGER DEFAULT 0,
+                content TEXT NOT NULL,
+                embedding BLOB,
+                content_hash TEXT,
+                freshness_score REAL DEFAULT 1.0,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            , user_id INTEGER DEFAULT 0, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE INDEX idx_pdocs_source ON project_docs(source_file)
+CREATE INDEX idx_pdocs_hash ON project_docs(content_hash)
+CREATE INDEX idx_pdocs_status ON project_docs(status)
+CREATE TABLE project_docs_meta (
+                source_file TEXT PRIMARY KEY,
+                source_version TEXT,
+                chunk_count INTEGER DEFAULT 0,
+                file_hash TEXT,
+                imported_at TEXT,
+                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE TABLE execution_notes (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT,
+                user_id INTEGER,
+                user_input TEXT NOT NULL,
+                summary TEXT,
+                outcome TEXT DEFAULT 'success',
+                steps_digest TEXT,
+                embedding BLOB,
+                content_hash TEXT,
+                status TEXT DEFAULT 'active',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP
+            )
+CREATE INDEX idx_exnotes_hash ON execution_notes(content_hash)
+CREATE INDEX idx_exnotes_task ON execution_notes(task_id)
+CREATE INDEX idx_exnotes_status ON execution_notes(status)
+CREATE TABLE attachments (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                file_id TEXT UNIQUE NOT NULL,
+                user_id INTEGER NOT NULL,
+                original_name TEXT,
+                stored_path TEXT NOT NULL,
+                mime_type TEXT,
+                size_bytes INTEGER DEFAULT 0,
+                kind TEXT DEFAULT 'file',
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                FOREIGN KEY (user_id) REFERENCES users(id)
+            )
+CREATE INDEX idx_attach_user ON attachments(user_id)
+CREATE INDEX idx_attach_fileid ON attachments(file_id)
+CREATE TABLE supervisor_runs (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                user_id INTEGER NOT NULL,
+                conversation_id INTEGER NOT NULL,
+                supervisor_id TEXT,
+                goal TEXT NOT NULL,
+                status TEXT DEFAULT 'running',
+                current_round INTEGER DEFAULT 0,
+                max_rounds INTEGER DEFAULT 5,
+                credits_used INTEGER DEFAULT 0,
+                history TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
+                finished_at TEXT
+            , task_type TEXT)
+CREATE INDEX idx_suprun_user ON supervisor_runs(user_id)
+CREATE TABLE credit_pool (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                amount REAL NOT NULL,
+                source TEXT,
+                created_at TEXT
+            )
+CREATE INDEX idx_credit_pool_time ON credit_pool(created_at)
+CREATE INDEX idx_yunchong_owner_status ON yunchong_tasks(owner_user_id, status)
+CREATE INDEX idx_yunchong_batch ON yunchong_tasks(batch_id)
+CREATE INDEX idx_yunchong_expires ON yunchong_tasks(expires_at)
+CREATE INDEX idx_memory_task ON safety_memory(task_id)
+CREATE INDEX idx_memory_hash ON safety_memory(content_hash)
+CREATE INDEX idx_memory_user_type ON safety_memory(user_id, memory_type)
+CREATE INDEX idx_swarm_pending_task ON swarm_pending_tasks(task_id)
+CREATE INDEX idx_swarm_pending_status ON swarm_pending_tasks(status)
+CREATE INDEX idx_swarm_pending_conv ON swarm_pending_tasks(conversation_id)
+CREATE INDEX idx_swarm_reviews_task ON swarm_reviews(task_id)
+CREATE INDEX idx_swarm_reviews_time ON swarm_reviews(created_at)
+CREATE INDEX idx_swarm_reviews_conversation ON swarm_reviews(conversation_id)
+CREATE TABLE task_feedback (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                task_id TEXT NOT NULL,
+                user_id INTEGER NOT NULL,
+                conversation_id INTEGER,
+                task_source TEXT NOT NULL,
+                feedback_type TEXT NOT NULL,
+                rating TEXT,
+                reason_tag TEXT,
+                reason_text TEXT,
+                task_snapshot TEXT NOT NULL,
+                result_snapshot TEXT NOT NULL,
+                metadata TEXT,
+                weight REAL DEFAULT 1.0,
+                is_latest INTEGER DEFAULT 1,
+                task_alive INTEGER DEFAULT 1,
+                created_at TEXT NOT NULL,
+                updated_at TEXT
+            , hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '')
+CREATE INDEX idx_feedback_task ON task_feedback(task_id)
+CREATE INDEX idx_feedback_user ON task_feedback(user_id, created_at)
+CREATE INDEX idx_feedback_rating ON task_feedback(rating, created_at)
+CREATE INDEX idx_feedback_reason ON task_feedback(reason_tag)
+CREATE INDEX idx_conversations_hlc ON conversations(hlc_ts)
+CREATE INDEX idx_conversations_shard ON conversations(shard_key)
+CREATE INDEX idx_group_members_hlc ON group_members(hlc_ts)
+CREATE INDEX idx_group_members_shard ON group_members(shard_key)
+CREATE INDEX idx_group_messages_hlc ON group_messages(hlc_ts)
+CREATE INDEX idx_group_messages_shard ON group_messages(shard_key)
+CREATE INDEX idx_groups_hlc ON groups(hlc_ts)
+CREATE INDEX idx_groups_shard ON groups(shard_key)
+CREATE INDEX idx_interaction_patterns_hlc ON interaction_patterns(hlc_ts)
+CREATE INDEX idx_interaction_patterns_shard ON interaction_patterns(shard_key)
+CREATE INDEX idx_knowledge_base_hlc ON knowledge_base(hlc_ts)
+CREATE INDEX idx_knowledge_base_shard ON knowledge_base(shard_key)
+CREATE INDEX idx_messages_hlc ON messages(hlc_ts)
+CREATE INDEX idx_messages_shard ON messages(shard_key)
+CREATE INDEX idx_project_docs_hlc ON project_docs(hlc_ts)
+CREATE INDEX idx_project_docs_shard ON project_docs(shard_key)
+CREATE INDEX idx_safety_memory_hlc ON safety_memory(hlc_ts)
+CREATE INDEX idx_safety_memory_shard ON safety_memory(shard_key)
+CREATE INDEX idx_space_nodes_hlc ON space_nodes(hlc_ts)
+CREATE INDEX idx_space_nodes_shard ON space_nodes(shard_key)
+CREATE INDEX idx_task_feedback_hlc ON task_feedback(hlc_ts)
+CREATE INDEX idx_task_feedback_shard ON task_feedback(shard_key)
+CREATE INDEX idx_users_hlc ON users(hlc_ts)
+CREATE INDEX idx_users_shard ON users(shard_key)
+CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)
+CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT UNIQUE NOT NULL, target_url TEXT NOT NULL, payload TEXT NOT NULL, headers TEXT, status TEXT NOT NULL DEFAULT 'pending', retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 5, next_retry_at TEXT NOT NULL, last_error TEXT, created_at TEXT NOT NULL, completed_at TEXT)
+CREATE INDEX idx_outbox_due ON outbox(status, next_retry_at)
+CREATE INDEX idx_outbox_msg ON outbox(msg_id)
+CREATE TABLE auth_meta (key TEXT PRIMARY KEY, value TEXT)
+CREATE TABLE nonce_cache (user_id INTEGER, nonce TEXT, expire_at TEXT, PRIMARY KEY (user_id, nonce))
+CREATE TABLE asset_snapshots (snapshot_date TEXT PRIMARY KEY, total_seed REAL NOT NULL, total_compute REAL NOT NULL, user_count INTEGER NOT NULL, tx_count INTEGER NOT NULL, ledger_hash TEXT NOT NULL, created_at TEXT NOT NULL)
+CREATE TABLE reconcile_issues (id INTEGER PRIMARY KEY AUTOINCREMENT, issue_type TEXT NOT NULL, detail TEXT, detected_at TEXT NOT NULL, resolved INTEGER DEFAULT 0, resolved_at TEXT, resolved_by TEXT)
+CREATE TABLE user_frozen (user_id INTEGER PRIMARY KEY, reason TEXT, frozen_at TEXT, frozen_by TEXT DEFAULT 'system')
+CREATE UNIQUE INDEX idx_transactions_idem ON transactions(idempotency_key) WHERE idempotency_key IS NOT NULL
+CREATE TABLE sync_received (
+                idempotency_key TEXT PRIMARY KEY,
+                received_at TEXT NOT NULL
+            )
```

## Node-A vs Node-B

```
--- Node-A
+++ Node-B
@@ -94,7 +94,7 @@
                 sender TEXT NOT NULL,
                 content TEXT NOT NULL,
                 sender_agent_id TEXT,
-                created_at TEXT DEFAULT CURRENT_TIMESTAMP, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', msg_type TEXT, attachments TEXT,
+                created_at TEXT DEFAULT CURRENT_TIMESTAMP, hlc_ts TEXT, origin_node TEXT, shard_key TEXT DEFAULT '', msg_type TEXT DEFAULT 'standard', attachments TEXT,
                 FOREIGN KEY (conversation_id) REFERENCES conversations(id)
             )
 CREATE TABLE agent_friendships (
@@ -780,45 +780,7 @@
 CREATE TABLE reconcile_issues (id INTEGER PRIMARY KEY AUTOINCREMENT, issue_type TEXT NOT NULL, detail TEXT, detected_at TEXT NOT NULL, resolved INTEGER DEFAULT 0, resolved_at TEXT, resolved_by TEXT)
 CREATE TABLE user_frozen (user_id INTEGER PRIMARY KEY, reason TEXT, frozen_at TEXT, frozen_by TEXT DEFAULT 'system')
 CREATE UNIQUE INDEX idx_transactions_idem ON transactions(idempotency_key) WHERE idempotency_key IS NOT NULL
-CREATE TABLE sync_received (idempotency_key TEXT PRIMARY KEY, received_at TEXT NOT NULL)
-CREATE TABLE api_registry (
-                api_id TEXT PRIMARY KEY,
-                endpoint TEXT NOT NULL,
-                description TEXT NOT NULL,
-                params_schema TEXT,
-                capability_tags TEXT,
-                provider_signature TEXT,
-                created_at TEXT NOT NULL
-            )
-CREATE TABLE nodes (
-            node_id TEXT PRIMARY KEY,
-            node_name TEXT,
-            role_type TEXT DEFAULT 'app_node',
-            public_key TEXT,
-            capabilities TEXT,
-            status TEXT DEFAULT 'offline',
-            last_heartbeat TEXT,
-            created_at TEXT NOT NULL
-        )
-CREATE TABLE cognitive_rules (
-            rule_id TEXT PRIMARY KEY,
-            domain_main TEXT NOT NULL,
-            domain_sub TEXT,
-            rule_content TEXT NOT NULL,
-            trigger_context TEXT,
-            confidence REAL DEFAULT 0.5,
-            applied_count INTEGER DEFAULT 0,
-            success_count INTEGER DEFAULT 0,
-            status TEXT DEFAULT 'active',
-            source_pattern_ids TEXT,
-            created_at TEXT NOT NULL,
-            updated_at TEXT
-        )
-CREATE TABLE rule_tool_bindings (
-            binding_id INTEGER PRIMARY KEY AUTOINCREMENT,
-            rule_id TEXT NOT NULL,
-            tool_id TEXT NOT NULL,
-            usage_context TEXT,
-            priority INTEGER DEFAULT 0,
-            FOREIGN KEY(rule_id) REFERENCES cognitive_rules(rule_id)
-        )
+CREATE TABLE sync_received (
+                idempotency_key TEXT PRIMARY KEY,
+                received_at TEXT NOT NULL
+            )
```
