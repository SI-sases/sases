import os
import re

def finish():
    print("🛠 正在完成最后的接线...")

    # 1. 挂载路由
    p_init = "core/api_routes/__init__.py"
    c_init = open(p_init, "r", encoding="utf-8").read()
    if "scheduled_routes" not in c_init:
        c_init = c_init.replace("from . import group_routes", "from . import group_routes\nfrom . import scheduled_routes\nfrom . import user_api_routes")
        open(p_init, "w", encoding="utf-8").write(c_init)
    
    p_boot = "core/bootstrap.py"
    c_boot = open(p_boot, "r", encoding="utf-8").read()
    if "scheduled_routes.router" not in c_boot:
        c_boot = c_boot.replace("app.include_router(group_routes.router)", "app.include_router(group_routes.router)\n    from .api_routes import scheduled_routes, user_api_routes\n    app.include_router(scheduled_routes.router)\n    app.include_router(user_api_routes.router)")
    
    # 2. 挂载后台调度器
    if "scheduled_task_scheduler" not in c_boot:
        # 加导入
        c_boot = c_boot.replace("async def lifespan(app: FastAPI):", "async def lifespan(app: FastAPI):\n    from .services.scheduled_scheduler import scheduled_task_scheduler")
        # 添加到后台任务列表
        c_boot = c_boot.replace("_background_tasks.append(asyncio.create_task(periodic_hlc_health()))", 
                                "_background_tasks.append(asyncio.create_task(periodic_hlc_health()))\n    _background_tasks.append(asyncio.create_task(scheduled_task_scheduler()))")
    open(p_boot, "w", encoding="utf-8").write(c_boot)
    print("✅ 1. 路由与调度器已接线")

    # 3. 修复 send.py 的参数透传与 #5 解析
    p_send = "core/services/message/send.py"
    c_send = open(p_send, "r", encoding="utf-8").read()

    # 3.1 补参数
    if "enabled_api_ids" not in c_send:
        # 找函数签名补齐
        c_send = re.sub(r'(def send_message\([^)]*?)(\)\s*:)', r'\1, enabled_api_ids=None\2', c_send, count=1)
        # 补齐 plan_task 透传
        c_send = c_send.replace("supervisor_run_id=_run_id,", "supervisor_run_id=_run_id,\n                            enabled_api_ids=enabled_api_ids,")
    
    # 3.2 注入 #5 解析
    if "#5:" not in c_send:
        logic = '''
    # ===== #5 定时任务解析 =====
    if _scan_content.strip().startswith('#5:') or _scan_content.strip().startswith('#5：'):
        import re
        from .. import scheduled_task_service
        
        _body = _scan_content.strip()[3:].lstrip('：: ')
        _match = re.match(r'每天(\\d+)点(?:(\\d+)分)?\\s+(.+)', _body)
        if _match:
            hour = int(_match.group(1))
            minute = int(_match.group(2)) if _match.group(2) else 0
            template = _match.group(3)
            cron = f"{minute} {hour} * * *"
            
            try:
                _cid = conversation_id
                _sid = sender_agent_id or agent_id
                
                _tid = scheduled_task_service.create_task(
                    user_id=user_id,
                    name=template[:10],
                    cron_expr=cron,
                    task_template=template,
                    conversation_id=_cid,
                    supervisor_id=_sid
                )
                _task = scheduled_task_service.get_task(_tid)
                _reply = f"✅ 定时任务已创建！\\n任务内容：{template}\\n执行时间：每天 {hour:02d}:{minute:02d}\\n下次执行：{_task['next_run_at'][:16]}"
            except Exception as _e:
                _reply = f"❌ 定时任务创建失败：{_e}"
        else:
            _reply = "❌ 格式错误。请使用：`#5: 每天5点 整理邮件` 或 `#5: 每天14点30分 备份数据库`"
            
        return {
            'conversation_id': conversation_id,
            'user_message': content,
            'assistant_reply': _reply,
            'agent_id': agent_id,
            'sender_agent_id': sender_agent_id,
            'mode': mode,
        }
    # =======================
'''
        anchor = "_scan_content = _normalize_prefix(content)"
        if anchor in c_send:
            c_send = c_send.replace(anchor, anchor + "\n" + logic)
    
    open(p_send, "w", encoding="utf-8").write(c_send)
    print("✅ 2. send.py 参数透传与 #5 解析已修复")

    # 4. 补齐 message_routes.py 和 commander.py
    p_routes = "core/api_routes/message_routes.py"
    c_routes = open(p_routes, "r", encoding="utf-8").read()
    if "enabled_api_ids" not in c_routes:
        c_routes = c_routes.replace("class SendMessageRequest(BaseModel):", "class SendMessageRequest(BaseModel):\n    enabled_api_ids: list = None")
        c_routes = c_routes.replace("mode=body.mode", "mode=body.mode,\n        enabled_api_ids=body.enabled_api_ids")
        open(p_routes, "w", encoding="utf-8").write(c_routes)

    p_cmd = "core/services/swarm/commander.py"
    c_cmd = open(p_cmd, "r", encoding="utf-8").read()
    if "enabled_api_ids" not in c_cmd:
        c_cmd = c_cmd.replace("max_steps: int = None\n) -> Dict[str, Any]:", "max_steps: int = None,\n    enabled_api_ids: list = None\n) -> Dict[str, Any]:")
        anchor = "_tools = _hr.harness_runtime.list_tools()"
        if anchor in c_cmd:
            new_anchor = """_tools = _hr.harness_runtime.list_tools()
        if enabled_api_ids:
            _tools = [t for t in _tools if t.get('id') in enabled_api_ids or f"ext_api_{t.get('id')}" in enabled_api_ids]"""
            c_cmd = c_cmd.replace(anchor, new_anchor)
        open(p_cmd, "w", encoding="utf-8").write(c_cmd)
    print("✅ 3. 全链路参数透传已打通")

if __name__ == "__main__":
    finish()