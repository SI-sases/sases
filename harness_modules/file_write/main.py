import os


def run(params):
    path = params.get('file_path')
    content = params.get('content', '')
    if not path:
        return {'ok': False, 'error': 'missing file_path'}
    if os.path.exists(path):
        return {'ok': False, 'error': 'file already exists: ' + path}
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'ok': True, 'file_path': path, 'bytes': len(content.encode('utf-8'))}
