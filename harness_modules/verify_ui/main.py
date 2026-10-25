import os
from playwright.sync_api import sync_playwright

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHOT_DIR = os.path.join(REPO_ROOT, 'static', '_ui_shots')

ALLOWED_URL_PREFIX = ('http://127.0.0.1:8001/', 'http://localhost:8001/')


def _check_url(url):
    if not url.startswith(ALLOWED_URL_PREFIX):
        raise ValueError('只允许本地 8001 端口')
    return url


def run(params):
    action = (params.get('action') or 'screenshot').lower()
    url = _check_url(params.get('url', 'http://127.0.0.1:8001/static/index.html'))
    timeout = int(params.get('timeout', 10000))

    result = {'success': True, 'action': action, 'url': url}

    try:
        os.makedirs(SHOT_DIR, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout, wait_until='networkidle')

            if action == 'screenshot':
                fname = params.get('filename') or 'shot.png'
                if not fname.endswith('.png'):
                    fname += '.png'
                fpath = os.path.join(SHOT_DIR, fname)
                page.screenshot(path=fpath, full_page=True)
                result['file'] = '/static/_ui_shots/' + fname
                result['bytes'] = os.path.getsize(fpath)

            elif action == 'check_element':
                selector = params.get('selector', '')
                if not selector:
                    raise ValueError('check_element 需要 selector')
                count = page.locator(selector).count()
                result['selector'] = selector
                result['exists'] = count > 0
                result['count'] = count
                if count == 0:
                    result['success'] = False

            elif action == 'get_text':
                selector = params.get('selector', '')
                if not selector:
                    raise ValueError('get_text 需要 selector')
                text = page.locator(selector).first.inner_text(timeout=3000)
                result['selector'] = selector
                result['text'] = text[:500]

            elif action == 'click':
                selector = params.get('selector', '')
                if not selector:
                    raise ValueError('click 需要 selector')
                page.locator(selector).first.click(timeout=5000)
                page.wait_for_timeout(500)
                result['clicked'] = selector

            else:
                raise ValueError('未知 action: ' + action)

            browser.close()
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)

    return result
