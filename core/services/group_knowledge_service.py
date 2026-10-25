"""群知识库服务 - 知识文档 + 汇报队列"""
import json
from ..db import db_cursor


def _check_admin(group_id, user_id):
    """检查用户是否是群主或管理员"""
    with db_cursor() as cur:
        cur.execute('SELECT owner_id FROM groups WHERE id=?', (group_id,))
        g = cur.fetchone()
        if not g:
            return False, 'group not found'
        if g['owner_id'] == user_id:
            return True, 'owner'
        cur.execute("SELECT role FROM group_members WHERE group_id=? AND user_id=?", (group_id, user_id))
        m = cur.fetchone()
        if m and m['role'] == 'admin':
            return True, 'admin'
    return False, 'not admin'


def _is_member(group_id, user_id):
    with db_cursor() as cur:
        cur.execute('SELECT id FROM group_members WHERE group_id=? AND user_id=?', (group_id, user_id))
        return cur.fetchone() is not None


# ========== 知识文档 CRUD ==========

def create_doc(group_id, user_id, title, content, category='doc', tags='', source_type='manual'):
    """创建知识条目（仅群主/管理员）"""
    ok, role = _check_admin(group_id, user_id)
    if not ok:
        return False, '只有群主或管理员可以添加'
    if not content or not content.strip():
        return False, '内容不能为空'
    with db_cursor(commit=True) as cur:
        cur.execute(
            'INSERT INTO knowledge_docs (scope, group_id, title, content, category, tags, source_type, contributor_id, visibility) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            ('group', group_id, title or '', content, category, tags, source_type, user_id, 'group')
        )
        doc_id = cur.lastrowid
    return True, {'doc_id': doc_id}


def list_docs(group_id, user_id, category=None, keyword=None, limit=50):
    """列出群知识库条目"""
    if not _is_member(group_id, user_id):
        return None
    with db_cursor() as cur:
        sql = "SELECT id, title, content, category, tags, contributor_id, hit_count, created_at FROM knowledge_docs WHERE scope='group' AND group_id=?"
        params = [group_id]
        if category:
            sql += ' AND category=?'
            params.append(category)
        if keyword:
            sql += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw])
        sql += ' ORDER BY id DESC LIMIT ?'
        params.append(limit)
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
    return rows


def get_doc(doc_id, user_id):
    """获取知识条目详情"""
    with db_cursor() as cur:
        cur.execute('SELECT * FROM knowledge_docs WHERE id=? AND scope=?', (doc_id, 'group'))
        d = cur.fetchone()
        if not d:
            return None
        if not _is_member(d['group_id'], user_id):
            return None
        cur.execute('UPDATE knowledge_docs SET hit_count = hit_count + 1 WHERE id=?', (doc_id,))
        return dict(d)


def delete_doc(doc_id, user_id):
    """删除知识条目（贡献者本人 or 群主/管理员）"""
    with db_cursor() as cur:
        cur.execute('SELECT group_id, contributor_id FROM knowledge_docs WHERE id=?', (doc_id,))
        d = cur.fetchone()
        if not d:
            return False, '文档不存在'
        ok, role = _check_admin(d['group_id'], user_id)
        if not ok and d['contributor_id'] != user_id:
            return False, '无权删除'
    with db_cursor(commit=True) as cur:
        cur.execute('DELETE FROM knowledge_docs WHERE id=?', (doc_id,))
    return True, {'deleted': doc_id}


def search_knowledge(group_id, query, top_k=5):
    """检索群知识库（供智能体调用），命中则返回条目"""
    if not query:
        return []
    with db_cursor() as cur:
        kw = f'%{query}%'
        cur.execute(
            "SELECT id, title, content, category FROM knowledge_docs WHERE scope='group' AND group_id=? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?) ORDER BY hit_count DESC LIMIT ?",
            (group_id, kw, kw, kw, top_k)
        )
        return [dict(r) for r in cur.fetchall()]


# ========== 汇报队列 ==========

def add_to_report_queue(group_id, user_id, question, anonymous=0, hit_kb_id=None):
    """员工提问未命中知识库时，进队列"""
    if not question or not question.strip():
        return False
    with db_cursor(commit=True) as cur:
        cur.execute(
            'INSERT INTO group_report_queue (group_id, question, asked_by, anonymous, hit_knowledge_id, status) VALUES (?, ?, ?, ?, ?, ?)',
            (group_id, question.strip(), user_id, anonymous, hit_kb_id, 'pending')
        )
        qid = cur.lastrowid
    return True, {'queue_id': qid}


def list_report_queue(group_id, user_id, status='pending', limit=50):
    """列出待补充的问题（仅群主/管理员）"""
    ok, role = _check_admin(group_id, user_id)
    if not ok:
        return None
    with db_cursor() as cur:
        cur.execute(
            'SELECT q.id, q.question, q.anonymous, q.asked_by, q.status, q.created_at, u.username FROM group_report_queue q LEFT JOIN users u ON q.asked_by = u.id WHERE q.group_id=? AND q.status=? ORDER BY q.id DESC LIMIT ?',
            (group_id, status, limit)
        )
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get('anonymous'):
                d['username'] = '匿名'
                d['asked_by'] = None
            rows.append(d)
    return rows


def resolve_report(group_id, user_id, queue_id, answer, category='faq'):
    """群主/管理员补充答案 → 自动入群知识库"""
    ok, role = _check_admin(group_id, user_id)
    if not ok:
        return False, '只有群主或管理员可以处理'
    with db_cursor() as cur:
        cur.execute('SELECT question FROM group_report_queue WHERE id=? AND group_id=?', (queue_id, group_id))
        q = cur.fetchone()
        if not q:
            return False, '问题不存在'
    # 先入知识库
    ok2, res = create_doc(group_id, user_id, title=q['question'][:50], content=answer, category=category, source_type='report')
    if not ok2:
        return False, res
    doc_id = res['doc_id']
    # 更新队列状态
    from datetime import datetime
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE group_report_queue SET status='resolved', resolved_kb_id=?, resolved_by=?, resolved_at=? WHERE id=?",
            (doc_id, user_id, datetime.utcnow().isoformat(), queue_id)
        )
    return True, {'doc_id': doc_id}


def ignore_report(group_id, user_id, queue_id):
    """忽略某条汇报（仅群主/管理员）"""
    ok, role = _check_admin(group_id, user_id)
    if not ok:
        return False, '只有群主或管理员可以操作'
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE group_report_queue SET status='ignored' WHERE id=? AND group_id=?", (queue_id, group_id))
        return True, {'ignored': queue_id}