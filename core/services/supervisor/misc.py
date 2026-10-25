def import_file_to_kb(file_url, original_name, user_id, supervisor_id=None):
    """把用户上传的文件导入项目库（仅 SASES 助手触发）"""
    if not supervisor_id or not (supervisor_id.startswith('sases_assistant') or supervisor_id.startswith('sases_api_')):
        return {'success': False, 'error': 'only sases assistant can import to kb'}
    import os as _os_i
    try:
        from .. import project_service
    except Exception as e:
        return {'success': False, 'error': 'project_service import failed: ' + str(e)}
    fn = (file_url or '').split('/')[-1]
    if not fn:
        return {'success': False, 'error': 'no filename'}
    fp = _os_i.path.join('uploads', fn)
    if not _os_i.path.exists(fp):
        return {'success': False, 'error': 'file not found'}
    try:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            raw = f.read()
    except Exception as e:
        return {'success': False, 'error': 'read failed: ' + str(e)}
    if not raw:
        return {'success': False, 'error': 'empty file'}
    src = original_name or fn
    try:
        n = project_service.import_document(src, 'v1.0-upload', raw, user_id=user_id)
    except Exception as e:
        return {'success': False, 'error': 'import failed: ' + str(e)}
    return {'success': True, 'chunks': n, 'file': src}
