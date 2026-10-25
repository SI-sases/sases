import os
import uuid
import base64
from datetime import datetime
from ..db import db_cursor

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')

ALLOWED_EXT = {
    '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.webp': 'image', '.bmp': 'image', '.svg': 'image',
    '.pdf': 'file', '.txt': 'file', '.md': 'file', '.zip': 'file', '.rar': 'file', '.7z': 'file', '.tar': 'file', '.gz': 'file',
    '.py': 'file', '.js': 'file', '.json': 'file', '.csv': 'file', '.html': 'file', '.css': 'file', '.xml': 'file', '.yaml': 'file', '.yml': 'file',
    '.doc': 'file', '.docx': 'file', '.xls': 'file', '.xlsx': 'file', '.ppt': 'file', '.pptx': 'file',
    '.mp3': 'file', '.mp4': 'file', '.wav': 'file', '.mov': 'file', '.avi': 'file',
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_FILE_BYTES = 25 * 1024 * 1024

MIME_MAP = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.gif': 'image/gif', '.webp': 'image/webp',
    '.pdf': 'application/pdf', '.txt': 'text/plain', '.md': 'text/markdown',
}


def _ensure_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def upload_base64(user_id, original_name, b64_data):
    if not original_name:
        return {'success': False, 'error': 'missing original_name'}
    if not b64_data:
        return {'success': False, 'error': 'missing base64'}
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXT:
        return {'success': False, 'error': 'unsupported ext: ' + ext}
    kind = ALLOWED_EXT[ext]
    try:
        raw = base64.b64decode(b64_data)
    except Exception as e:
        return {'success': False, 'error': 'base64 decode failed: ' + str(e)}
    size = len(raw)
    limit = MAX_IMAGE_BYTES if kind == 'image' else MAX_FILE_BYTES
    if size > limit:
        return {'success': False, 'error': 'too large'}
    _ensure_dir()
    file_id = uuid.uuid4().hex
    stored_name = file_id + ext
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    try:
        with open(stored_path, 'wb') as f:
            f.write(raw)
    except Exception as e:
        return {'success': False, 'error': 'write failed: ' + str(e)}
    mime = MIME_MAP.get(ext, 'application/octet-stream')
    now = datetime.now().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute('INSERT INTO attachments (file_id, user_id, original_name, stored_path, mime_type, size_bytes, kind, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (file_id, user_id, original_name, stored_name, mime, size, kind, now))
    return {'success': True, 'file_id': file_id, 'url': '/uploads/' + stored_name, 'original_name': original_name, 'mime_type': mime, 'size_bytes': size, 'kind': kind}


def get_attachment(file_id):
    with db_cursor() as cur:
        cur.execute('SELECT * FROM attachments WHERE file_id=?', (file_id,))
        row = cur.fetchone()
    return dict(row) if row else None