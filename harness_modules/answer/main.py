"""输出最终答案工具"""


def run(params):
    content = params.get('content', '')
    if not content:
        return {'success': False, 'error': 'missing content'}
    if len(content) > 5000:
        content = content[:5000] + '...'
    return {'success': True, 'answer': content, 'length': len(content)}