import os
import sqlite3

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(REPO_ROOT, 'users.db')
DEFAULT_USER = 2


def run(params):
    source_file = params.get('source_file', '').strip()
    try:
        user_id = int(params.get('user_id', DEFAULT_USER))
    except Exception:
        user_id = DEFAULT_USER
    if not os.path.exists(DB_PATH):
        return {'success': False, 'error': 'users.db not found'}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if not source_file:
            cur.execute("""
                SELECT source_file, COUNT(*) as chunk_count, MAX(updated_at) as updated_at
                FROM project_docs
                WHERE user_id=? AND status='active'
                GROUP BY source_file
                ORDER BY MAX(updated_at) DESC
            """, (user_id,))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return {'success': True, 'user_id': user_id, 'documents': rows}
        cur.execute("""
            SELECT section_title, content, chunk_index
            FROM project_docs
            WHERE user_id=? AND source_file=? AND status='active'
            ORDER BY chunk_index ASC
        """, (user_id, source_file))
        chunks = cur.fetchall()
        conn.close()
        if not chunks:
            return {'success': False, 'error': 'doc not found: ' + source_file}
        parts = []
        for c in chunks:
            if c['section_title']:
                parts.append('## ' + c['section_title'] + chr(10) + chr(10) + c['content'])
            else:
                parts.append(c['content'])
        return {
            'success': True,
            'user_id': user_id,
            'source_file': source_file,
            'chunk_count': len(chunks),
            'content': (chr(10) + chr(10)).join(parts)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
