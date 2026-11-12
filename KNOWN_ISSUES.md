 
## 2026-11-12 P2 遗留：supervisor 续轮崩溃 
 
- 现象：`[supervisor] 续轮失败: name 'run' is not defined` + `finish_run -
- 影响：任务只执行 1 步就结束，用户看到"OK 执行已结束"是假完成 
- 定位：`core/services/supervisor/continuation.py` 或 `core/services/swarm/executor_callback.py` 里的 `check_and_continue` 
- 修复：P0-E 完成后处理，优先级中 
