 
## 2026-11-12 P2 supervisor ֱ 
 
- `[supervisor] ʧ: name 'run' is not defined` + `finish_run -
- Ӱ죺ִֻ 1 ͽû"OK ִѽ"Ǽ 
- λ`core/services/supervisor/continuation.py`  `core/services/swarm/executor_callback.py`  `check_and_continue` 
- ޸P0-E ɺȼ 

## 2026-11-12 P0 后待处理

- [高] build_portable.py 必须含 core/keys/license_pub.pem（否则客户端无法激活）
- [中] P2 遗留 supervisor 续轮崩溃（name run is not defined）
- [中] ok_legacy_plaintext 是过渡方案，签 license.json 前端改造后应关掉
- [低] check_exec 的 free_mode 分支不写审计
- [低] license.json 的 user_id 不参与本地校验，靠云端 (user_id, fp) 匹配保护，需文档化

## 2026-11-13 P2 遗留已修复

- [x] supervisor 续轮崩溃：continuation.py:135 无条件 return + decider.py:47 run 未定义，均已修
- [x] 多轮任务能真正跑完，finish_run 状态从 error 变 completed
