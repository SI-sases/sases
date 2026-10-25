import os
import json
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)
MAX_INPUT = 8000


def _get_api_key():
    key = os.environ.get('DEEPSEEK_API_KEY', '')
    if key:
        return key
    env_path = os.path.join(REPO_ROOT, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('DEEPSEEK_API_KEY='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''


def _read_file(path):
    if not path:
        return None
    p = path.replace(BACKSLASH, '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        return None
    if '..' in p.split('/'):
        return None
    abs_path = os.path.join(REPO_ROOT, p)
    if not os.path.exists(abs_path):
        return None
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(MAX_INPUT)
    except Exception:
        return None


def _call_llm(prompt, api_key):
    url = 'https://api.deepseek.com/v1/chat/completions'
    body = {
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.3,
        'max_tokens': 1500
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', 'Bearer ' + api_key)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            r = json.loads(resp.read().decode('utf-8'))
            return r['choices'][0]['message']['content']
    except Exception as e:
        return None


def run(params):
    source_file = params.get('source_file', '').strip()
    text = params.get('text', '').strip()
    max_points = int(params.get('max', 10))
    if not source_file and not text:
        return {'success': False, 'error': 'need source_file or text'}
    if source_file:
        text = _read_file(source_file)
        if text is None:
            return {'success': False, 'error': 'file unreadable: ' + source_file}
    text = text[:MAX_INPUT]
    api_key = _get_api_key()
    if not api_key:
        return {'success': False, 'error': 'no api key'}
    prompt = '请从以下内容中提取最多 ' + str(max_points) + ' 个关键要点。每条一行，以数字编号开头。只输出要点列表，不要解释。\n\n内容：\n' + text
    result = _call_llm(prompt, api_key)
    if result is None:
        return {'success': False, 'error': 'llm call failed'}
    return {
        'success': True,
        'source_file': source_file or 'text',
        'max_points': max_points,
        'keypoints': result
    }
