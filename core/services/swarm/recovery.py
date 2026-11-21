# core/services/swarm/recovery.py
# -*- coding: utf-8 -*-
"""D: 执行恢复门面（租约/步骤日志/截止/回收），执行器只依赖这一层。"""
from .. import run_journal as _j

acquire_lease = _j.acquire_lease
heartbeat = _j.heartbeat
release = _j.release
set_deadline = _j.set_deadline
deadline_expired = _j.deadline_expired
step_begin = _j.step_begin
step_end = _j.step_end
done_step_ids = _j.done_step_ids
recover_stale = _j.recover_stale
is_stalled = _j.is_stalled
is_cancelled = _j.is_cancelled
mark_interrupted = _j.mark_interrupted
