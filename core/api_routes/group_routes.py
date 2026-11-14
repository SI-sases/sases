# core/api_routes/group_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import group_service

router = APIRouter(prefix="/group", tags=["group"])
@router.post("/group/{group_id}/leave")
async def api_leave_group(group_id: int):
    return group_service.leave_group(group_id)

@router.post("/group/{group_id}/dismiss")
async def api_dismiss_group(group_id: int):
    return group_service.dismiss_group(group_id)

security = HTTPBearer()


class GroupCreateRequest(BaseModel):
    name: str


class GroupInviteRequest(BaseModel):
    group_id: int
    username_or_id: str


class GroupMessageRequest(BaseModel):
    content: str
    agent_id: Optional[str] = None


class GroupRemoveMemberRequest(BaseModel):
    username_or_id: str


class GroupModeRequest(BaseModel):
    mode: str  # normal 或 swarm


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/create")
async def create_group(body: GroupCreateRequest, user_id: int = Depends(get_current_user)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="群名称不能为空")
    group_id = group_service.create_group(body.name.strip(), user_id)
    return {"group_id": group_id, "name": body.name.strip()}


@router.post("/invite")
async def invite_to_group(body: GroupInviteRequest, user_id: int = Depends(get_current_user)):
    success, msg = group_service.invite_to_group(body.group_id, user_id, body.username_or_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "invited"}


@router.get("/list")
async def list_my_groups(user_id: int = Depends(get_current_user)):
    groups = group_service.list_user_groups(user_id)
    return {"groups": groups}


@router.get("/{group_id}/info")
async def get_group_info(group_id: int, user_id: int = Depends(get_current_user)):
    info = group_service.get_group_info(group_id)
    if not info:
        raise HTTPException(status_code=404, detail="群不存在")
    return info


@router.get("/{group_id}/messages")
async def get_group_messages(group_id: int, user_id: int = Depends(get_current_user)):
    messages = group_service.get_group_messages(group_id, user_id)
    if messages is None:
        raise HTTPException(status_code=403, detail="你不是群成员")
    return {"messages": messages}


@router.post("/{group_id}/messages")
async def send_group_message(group_id: int, body: GroupMessageRequest, user_id: int = Depends(get_current_user)):
    success, msg = group_service.send_group_message(group_id, user_id, body.content, body.agent_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    try:
        from .ws_routes import broadcast_to_group
        from ..db import db_cursor
        with db_cursor() as cur:
            cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _r = cur.fetchone()
        if _r and _r['global_group_id']:
            with db_cursor() as _cur_n:
                _cur_n.execute('SELECT username FROM users WHERE id=?', (user_id,))
                _u_n = _cur_n.fetchone()
                _sname = _u_n['username'] if _u_n else '?'
            await broadcast_to_group(_r['global_group_id'], {
                'type': 'message',
                'content': body.content,
                'sender_id': user_id,
                'sender_agent_id': body.agent_id,
                'sender_name': _sname,
            })
    except Exception as _e:
        print('[ws] push failed:', _e)
    # 检测 @智能体 触发 AI 回复
    if not body.agent_id:
        import asyncio as _aio
        _aio.create_task(_handle_at_agent(group_id, user_id, body.content))
    return {"status": "sent"}


async def _handle_at_agent(group_id, user_id, content):
    """@智能体触发 AI 回复（异步后台）"""
    from ..services import group_service, group_resource_service
    from ..db import db_cursor
    agent_name, question = group_service.parse_at_prefix(content)
    if not agent_name:
        return
    if group_service._is_human_in_group(group_id, agent_name):
        return
    agent_id = group_service._find_agent_id_by_name(group_id, agent_name)
    if not agent_id:
        return
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_resource_pool WHERE group_id=? AND agent_id=? AND enabled=1", (group_id, agent_id))
        if not cur.fetchone():
            return
    if not question:
        question = '你好'
    ok, reply = await group_resource_service.call_agent_with_group_resource(group_id, user_id, agent_id, question)
    if not ok:
        reply = f'⚠️ ' + str(reply)
    group_service.insert_agent_message(group_id, agent_id, reply, trigger_user_id=user_id)
    try:
        from .ws_routes import broadcast_to_group
        with db_cursor() as cur:
            cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _r = cur.fetchone()
        if _r and _r['global_group_id']:
            await broadcast_to_group(_r['global_group_id'], {
                'type': 'message',
                'content': reply,
                'sender_id': None,
                'sender_agent_id': agent_id,
            })
    except Exception as _e:
        print('[at-agent] ws push failed:', _e)


@router.get("/{group_id}/members")
async def get_group_members(group_id: int, user_id: int = Depends(get_current_user)):
    members = group_service.list_group_members(group_id)
    return {"members": members}


@router.get("/{group_id}/credits")
async def get_group_credits(group_id: int, user_id: int = Depends(get_current_user)):
    credits = group_service.get_group_credits(group_id)
    return {"credits": credits}


@router.post("/{group_id}/remove-member")
async def remove_member(group_id: int, body: GroupRemoveMemberRequest, user_id: int = Depends(get_current_user)):
    success, msg = group_service.remove_member_from_group(group_id, user_id, body.username_or_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "removed"}


@router.post("/{group_id}/pin")
async def toggle_pin(group_id: int, body: dict, user_id: int = Depends(get_current_user)):
    pinned = bool(body.get('pinned'))
    ok = group_service.toggle_group_pin(group_id, user_id, pinned)
    if not ok:
        raise HTTPException(status_code=403, detail='not a member')
    return {'group_id': group_id, 'pinned': pinned}



@router.post("/{group_id}/read")
async def mark_read(group_id: int, user_id: int = Depends(get_current_user)):
    ok = group_service.mark_group_read(group_id, user_id)
    return {'group_id': group_id, 'read': ok}



@router.post("/{group_id}/mode")
async def set_group_mode(group_id: int, body: GroupModeRequest, user_id: int = Depends(get_current_user)):
    if body.mode not in ("normal", "swarm"):
        raise HTTPException(status_code=400, detail="模式只能是 normal 或 swarm")
    success, msg = group_service.set_group_mode(group_id, body.mode, user_id)
    if not success:
        raise HTTPException(status_code=403, detail=msg)
    return {"status": "updated", "mode": body.mode}



class TaskPublishRequest(BaseModel):
    title: str
    description: str = ''
    category: str = 'text'
    reward: float = 0


class TaskSubmitRequest(BaseModel):
    content: str
    content_type: str = 'text'
    agent_id: Optional[str] = None


class TaskSelectRequest(BaseModel):
    submission_id: int


class TaskRejectRequest(BaseModel):
    reason: str = ''


@router.post("/{group_id}/tasks/publish")
async def api_publish_task(group_id: int, body: TaskPublishRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.publish_task(group_id, user_id, body.title, body.description, body.category, body.reward)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    try:
        import json as _json_b
        from .ws_routes import broadcast_to_group
        from ..db import db_cursor as _dc_b
        with _dc_b() as _cur_b:
            _cur_b.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _r_b = _cur_b.fetchone()
        if _r_b and _r_b['global_group_id']:
            await broadcast_to_group(_r_b['global_group_id'], {
                'type': 'message',
                'content': '[TASK_CARD]:' + _json_b.dumps({
                    'task_id': res['task_id'],
                    'title': body.title,
                    'reward': body.reward,
                    'status': 'open'
                }, ensure_ascii=False),
                'sender_id': None,
                'sender_agent_id': None,
                'sender_name': '系统'
            })
    except Exception as _e_b:
        print('[ws] publish broadcast failed:', _e_b)
    return res


@router.get("/{group_id}/tasks")
async def api_list_tasks(group_id: int, status: Optional[str] = None, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    return {"tasks": group_task_service.list_tasks(group_id, status)}


@router.get("/tasks/{task_id}")
async def api_get_task(task_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    task = group_task_service.get_task_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.post("/tasks/{task_id}/submit")
async def api_submit_task(task_id: int, body: TaskSubmitRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.submit_solution(task_id, user_id, body.agent_id, body.content, body.content_type)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/tasks/{task_id}/select")
async def api_select_task(task_id: int, body: TaskSelectRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.select_winner(task_id, user_id, body.submission_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/tasks/{task_id}/reject")
async def api_reject_task(task_id: int, body: TaskRejectRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_task_service
    ok, res = group_task_service.reject_all(task_id, user_id, body.reason)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


class StakeRequest(BaseModel):
    amount: float


class RedPacketConfigRequest(BaseModel):
    hour: int
    audience: str = 'all'


@router.post("/{group_id}/stake")
async def api_stake(group_id: int, body: StakeRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.stake_credits(group_id, user_id, body.amount)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/{group_id}/stake/withdraw")
async def api_withdraw_stake(group_id: int, user_id: int = Depends(get_current_user)):
    ok, res = group_service.withdraw_stake(group_id, user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/{group_id}/stakes")
async def api_list_stakes(group_id: int, user_id: int = Depends(get_current_user)):
    return {"stakes": group_service.list_active_stakes(group_id)}


@router.get("/{group_id}/pool")
async def api_group_pool(group_id: int, user_id: int = Depends(get_current_user)):
    detail = group_service.get_group_pool_detail(group_id)
    if not detail:
        raise HTTPException(status_code=404, detail="group not found")
    return detail


@router.post("/{group_id}/red-packet/config")
async def api_config_red_packet(group_id: int, body: RedPacketConfigRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.configure_red_packet(group_id, user_id, body.hour, body.audience)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/{group_id}/red-packet/send")
async def api_send_red_packet(group_id: int, user_id: int = Depends(get_current_user)):
    ok, res = group_service.distribute_group_red_packet(group_id, user_id)
class GroupRedPacketCreateRequest(BaseModel):
    total_amount: float
    total_count: int
    message: str = ''
    source_type: str = 'user'
    packet_type: str = 'lucky'


@router.post("/{group_id}/red-packets/create")
async def api_create_group_red_packet(group_id: int, body: GroupRedPacketCreateRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    ok, res = group_red_packet_service.create_packet(group_id, user_id, body.total_amount, body.total_count, body.message, body.source_type, getattr(body, "packet_type", "lucky"))
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    # v0.42.0: 红包创建后触发 WS 广播
    try:
        from .ws_routes import broadcast_to_group
        from ..db import db_cursor
        with db_cursor() as cur:
            cur.execute("SELECT global_group_id FROM groups WHERE id=?", (group_id,))
            _rg = cur.fetchone()
            cur.execute("SELECT id, content FROM group_messages WHERE group_id=? AND message_type='red_packet' ORDER BY id DESC LIMIT 1", (group_id,))
            _rm = cur.fetchone()
        if _rg and _rg['global_group_id'] and _rm:
            with db_cursor() as _cur_n:
                _cur_n.execute('SELECT username FROM users WHERE id=?', (user_id,))
                _u_n = _cur_n.fetchone()
                _sname = _u_n['username'] if _u_n else '?'
            await broadcast_to_group(_rg['global_group_id'], {
                'type': 'message',
                'content': _rm['content'],
                'message_id': _rm['id'],
                'sender_id': user_id,
                'sender_name': _sname,
                'message_type': 'red_packet',
            })
    except Exception as _e:
        print('[ws] red packet push failed:', _e)
    return res


@router.post("/red-packets/{packet_id}/claim")
async def api_claim_group_red_packet(packet_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    ok, res = group_red_packet_service.claim_packet(packet_id, user_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/red-packets/{packet_id}")
async def api_get_group_red_packet(packet_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    detail = group_red_packet_service.get_packet_detail(packet_id, user_id)
    if not detail:
        raise HTTPException(status_code=404, detail="红包不存在")
    return detail


@router.get("/{group_id}/red-packets/active")
async def api_list_active_group_red_packets(group_id: int, user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail='你不是群成员')
        cur.execute("SELECT id, sender_id, total_amount, total_count, claimed_count, packet_type, source_type, message, created_at, expires_at FROM group_red_packets WHERE group_id=? AND status='active' AND (expires_at IS NULL OR expires_at > ?) AND id NOT IN (SELECT packet_id FROM group_red_packet_claims WHERE user_id=?) ORDER BY id DESC", (group_id, now, user_id))
        rows = [dict(r) for r in cur.fetchall()]
    return {'packets': rows}



@router.get("/{group_id}/leaderboard")
async def api_group_leaderboard(group_id: int, type: str = 'contribution', user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail='你不是群成员')
        if type == 'contribution':
            cur.execute('SELECT u.id, u.username, COALESCE(gm.contribution_points, 0) as score FROM group_members gm LEFT JOIN users u ON gm.user_id = u.id WHERE gm.group_id=? AND gm.user_id IS NOT NULL ORDER BY score DESC LIMIT 50', (group_id,))
        elif type == 'task':
            cur.execute("SELECT u.id, u.username, COUNT(*) * 10 as score FROM group_task_submissions s JOIN group_tasks t ON s.task_id = t.id LEFT JOIN users u ON s.submitted_by = u.id WHERE t.group_id=? AND t.selected_submission_id = s.id GROUP BY u.id ORDER BY score DESC LIMIT 50", (group_id,))
        elif type == 'redpacket':
            cur.execute('SELECT u.id, u.username, COALESCE(SUM(c.amount), 0) as score FROM group_red_packet_claims c LEFT JOIN users u ON c.user_id = u.id LEFT JOIN group_red_packets p ON c.packet_id = p.id WHERE p.group_id=? GROUP BY u.id ORDER BY score DESC LIMIT 50', (group_id,))
        else:
            raise HTTPException(status_code=400, detail='未知榜单类型')
        rows = [dict(r) for r in cur.fetchall()]
    return {'type': type, 'leaderboard': rows}



class KnowledgeCreateRequest(BaseModel):
    title: str = ''
    content: str
    category: str = 'doc'
    tags: str = ''


class ReportResolveRequest(BaseModel):
    answer: str
    category: str = 'faq'


@router.post("/{group_id}/knowledge")
async def api_create_knowledge(group_id: int, body: KnowledgeCreateRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    ok, res = group_knowledge_service.create_doc(group_id, user_id, body.title, body.content, body.category, body.tags)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/{group_id}/knowledge")
async def api_list_knowledge(group_id: int, category: Optional[str] = None, keyword: Optional[str] = None, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    docs = group_knowledge_service.list_docs(group_id, user_id, category, keyword)
    if docs is None:
        raise HTTPException(status_code=403, detail='你不是群成员')
    return {'docs': docs}


@router.get("/knowledge/{doc_id}")
async def api_get_knowledge(doc_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    d = group_knowledge_service.get_doc(doc_id, user_id)
    if not d:
        raise HTTPException(status_code=404, detail='知识不存在')
    return d


@router.delete("/knowledge/{doc_id}")
async def api_delete_knowledge(doc_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    ok, res = group_knowledge_service.delete_doc(doc_id, user_id)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.get("/{group_id}/report-queue")
async def api_list_report_queue(group_id: int, status: str = 'pending', user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    rows = group_knowledge_service.list_report_queue(group_id, user_id, status)
    if rows is None:
        raise HTTPException(status_code=403, detail='只有群主或管理员可以查看')
    return {'items': rows}


@router.post("/{group_id}/report-queue")
async def api_add_report(group_id: int, body: dict, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    question = body.get('question', '')
    ok, res = group_knowledge_service.add_to_report_queue(group_id, user_id, question)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/report-queue/{queue_id}/resolve")
async def api_resolve_report(queue_id: int, body: ReportResolveRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute('SELECT group_id FROM group_report_queue WHERE id=?', (queue_id,))
        r = cur.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail='问题不存在')
    ok, res = group_knowledge_service.resolve_report(r['group_id'], user_id, queue_id, body.answer, body.category)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.post("/report-queue/{queue_id}/ignore")
async def api_ignore_report(queue_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_knowledge_service
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute('SELECT group_id FROM group_report_queue WHERE id=?', (queue_id,))
        r = cur.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail='问题不存在')
    ok, res = group_knowledge_service.ignore_report(r['group_id'], user_id, queue_id)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res



class BindAgentModelRequest(BaseModel):
    agent_id: str
    model_id: str
    daily_limit: int = 100


class SwarmToggleRequest(BaseModel):
    enabled: bool


@router.get("/{group_id}/swarm/status")
async def api_swarm_status(group_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    return {"swarm_enabled": group_resource_service.is_swarm_enabled(group_id)}


@router.post("/{group_id}/swarm/toggle")
async def api_swarm_toggle(group_id: int, body: SwarmToggleRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    ok, res = group_resource_service.toggle_swarm(group_id, user_id, body.enabled)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.get("/{group_id}/resource-pool")
async def api_list_resource_pool(group_id: int, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    rows = group_resource_service.list_pool(group_id, user_id)
    if rows is None:
        raise HTTPException(status_code=403, detail='你不是群成员')
    return {'pool': rows, 'swarm_enabled': group_resource_service.is_swarm_enabled(group_id)}


@router.post("/{group_id}/resource-pool/bind")
async def api_bind_agent_model(group_id: int, body: BindAgentModelRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    ok, res = group_resource_service.bind_agent_model(group_id, user_id, body.agent_id, body.model_id, body.daily_limit)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.post("/{group_id}/resource-pool/unbind")
async def api_unbind_agent(group_id: int, body: dict, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    agent_id = body.get('agent_id', '')
    ok, res = group_resource_service.unbind_agent(group_id, user_id, agent_id)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.get("/{group_id}/resource-usage")
async def api_resource_usage(group_id: int, days: int = 7, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    stats = group_resource_service.get_usage_stats(group_id, user_id, days)
    if stats is None:
        raise HTTPException(status_code=403, detail='只有群主可以查看')
    return stats


@router.get("/{group_id}/quota-check")
async def api_quota_check(group_id: int, agent_id: str, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    ok, res = group_resource_service.check_quota(group_id, user_id, agent_id)
    return {'ok': ok, 'detail': res}



class SetMemberRoleRequest(BaseModel):
    username_or_id: str
    role: str


@router.get("/{group_id}/admins")
async def api_list_group_admins(group_id: int, user_id: int = Depends(get_current_user)):
    return {"admins": group_service.list_admins(group_id)}


@router.post("/{group_id}/members/role")
async def api_set_member_role(group_id: int, body: SetMemberRoleRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.set_member_role(group_id, user_id, body.username_or_id, body.role)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res



class GroupAiSuggestRequest(BaseModel):
    agent_id: str
    question: str


@router.post("/{group_id}/ai-suggest")
async def api_group_ai_suggest(group_id: int, body: GroupAiSuggestRequest, user_id: int = Depends(get_current_user)):
    from ..services import group_resource_service
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="你不是群成员")
        cur.execute("SELECT id FROM group_resource_pool WHERE group_id=? AND agent_id=? AND enabled=1", (group_id, body.agent_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="该智能体未共享给本群")
    ok, reply = await group_resource_service.call_agent_with_group_resource(group_id, user_id, body.agent_id, body.question)
    if not ok:
        raise HTTPException(status_code=400, detail=reply)
    return {"response": reply}



class AnnouncementRequest(BaseModel):
    content: str


@router.get("/{group_id}/announcement")
async def api_get_announcement(group_id: int, user_id: int = Depends(get_current_user)):
    return {"announcement": group_service.get_announcement(group_id)}


@router.post("/{group_id}/announcement")
async def api_set_announcement(group_id: int, body: AnnouncementRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.set_announcement(group_id, user_id, body.content)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res



class TransferOwnerRequest(BaseModel):
    username_or_id: str


@router.post("/{group_id}/transfer-owner")
async def api_transfer_owner(group_id: int, body: TransferOwnerRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.transfer_owner(group_id, user_id, body.username_or_id)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res



class InviteConfirmRequest(BaseModel):
    enabled: bool


@router.get("/{group_id}/invite-confirm")
async def api_get_invite_confirm(group_id: int, user_id: int = Depends(get_current_user)):
    return {"enabled": group_service.get_invite_confirm(group_id)}


@router.post("/{group_id}/invite-confirm")
async def api_set_invite_confirm(group_id: int, body: InviteConfirmRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.set_invite_confirm(group_id, user_id, body.enabled)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.get("/{group_id}/pending-invites")
async def api_list_pending_invites(group_id: int, user_id: int = Depends(get_current_user)):
    rows = group_service.list_pending_invites(group_id, user_id)
    if rows is None:
        raise HTTPException(status_code=403, detail="只有群主或管理员可以查看")
    return {"items": rows}


@router.post("/pending-invites/{pending_id}/approve")
async def api_approve_invite(pending_id: int, body: dict, user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT group_id FROM group_invite_pending WHERE id=?", (pending_id,))
        r = cur.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="待批准记录不存在")
    ok, res = group_service.approve_invite(r['group_id'], user_id, pending_id)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.post("/pending-invites/{pending_id}/reject")
async def api_reject_invite(pending_id: int, body: dict, user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT group_id FROM group_invite_pending WHERE id=?", (pending_id,))
        r = cur.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="待批准记录不存在")
    ok, res = group_service.reject_invite(r['group_id'], user_id, pending_id)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res



@router.get("/{group_id}/files")
async def api_list_group_files(group_id: int, user_id: int = Depends(get_current_user)):
    files = group_service.list_group_files(group_id, user_id)
    if files is None:
        raise HTTPException(status_code=403, detail="你不是群成员")
    return {"files": files}



class GroupNameRequest(BaseModel):
    name: str


class NicknameRequest(BaseModel):
    nickname: str


class MuteRequest(BaseModel):
    muted: bool


@router.patch("/{group_id}/name")
async def api_update_group_name(group_id: int, body: GroupNameRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.update_group_name(group_id, user_id, body.name)
    if not ok:
        raise HTTPException(status_code=403, detail=res)
    return res


@router.patch("/{group_id}/nickname")
async def api_set_nickname(group_id: int, body: NicknameRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.set_my_nickname(group_id, user_id, body.nickname)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res


@router.patch("/{group_id}/mute")
async def api_toggle_mute(group_id: int, body: MuteRequest, user_id: int = Depends(get_current_user)):
    ok, res = group_service.toggle_mute(group_id, user_id, body.muted)
    return res


@router.get("/{group_id}/search-messages")
async def api_search_group_messages(group_id: int, q: str, user_id: int = Depends(get_current_user)):
    from ..db import db_cursor
    with db_cursor() as cur:
        cur.execute("SELECT id FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="你不是群成员")
        kw = f'%{q}%'
        cur.execute("SELECT id, content, sender_id, sender_agent_id, created_at FROM group_messages WHERE group_id=? AND content LIKE ? ORDER BY id DESC LIMIT 50", (group_id, kw))
        rows = [dict(r) for r in cur.fetchall()]
    return {"messages": rows}



@router.post("/red-packets/expire")
async def api_expire_group_red_packets(user_id: int = Depends(get_current_user)):
    from ..services import group_red_packet_service
    expired = group_red_packet_service.expire_packets()
    return {"expired": expired, "count": len(expired)}



    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return res

