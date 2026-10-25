import base64
import json
import httpx
from datetime import datetime
from ...db import db_cursor
from .model_call import call_model_with_config

def _enrich_attachment(content):
    """[IMAGE]:/[FILE]: 消息 → 附加内容描述，供模型理解"""
    import os as _os, base64 as _b64, glob as _glob
    try:
        _prefix, _rest = content.split(':', 1)
        # support [FILE]:/uploads/xxx|filename|size
        _rel = _rest.split('|')[0].strip().lstrip('/')
    except Exception:
        return content
    _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    _abs = _os.path.join(_root, _rel)
    if not _os.path.exists(_abs):
        return content + ' (文件不存在)'
    if content.startswith('[FILE]:'):
        try:
            _txt = open(_abs, 'r', encoding='utf-8', errors='replace').read(5000)
            return '[用户发了一个文件 ' + _rel + '，内容如下]' + chr(10) + _txt
        except Exception as _e:
            return content + ' (读文件失败: ' + str(_e) + ')'
    if content.startswith('[IMAGE]:'):
        try:
            from ... import config as _cfg
            import openai as _oai
            _raw = open(_abs, 'rb').read()
            if len(_raw) > 4 * 1024 * 1024:
                return content + ' (图片过大)'
            _mime = 'image/png'
            _low = _rel.lower()
            if _low.endswith('.jpg') or _low.endswith('.jpeg'):
                _mime = 'image/jpeg'
            elif _low.endswith('.gif'):
                _mime = 'image/gif'
            elif _low.endswith('.webp'):
                _mime = 'image/webp'
            _b64s = _b64.b64encode(_raw).decode()
            _cli = _oai.OpenAI(api_key=_cfg.DEEPSEEK_API_KEY, base_url=_cfg.DEEPSEEK_BASE_URL, timeout=30)
            _r = _cli.chat.completions.create(
                model=_cfg.VISION_MODEL_NAME,
                messages=[{'role': 'user', 'content': [
                    {'type': 'text', 'text': '直接描述图片的内容、文字、场景，100字以内。只输出描述本身，禁止输出任何分析过程、思考步骤或格式说明。'},
                    {'type': 'image_url', 'image_url': {'url': 'data:' + _mime + ';base64,' + _b64s}}
                ]}],
                max_tokens=300
            )
            _desc = (_r.choices[0].message.content or '').strip()
            if not _desc:
                _rc = getattr(_r.choices[0].message, 'reasoning_content', None) or ''
                _rc_lines = [l.strip() for l in _rc.split(chr(10)) if l.strip()]
                _desc = _rc_lines[-1][:200] if _rc_lines else ''
            # 过滤推理痕迹
            if any(_kw in _desc for _kw in ('我们需要', '分析用户', '任务：', '让我', '步骤', '首先是')):
                _sents = [_s.strip() for _s in _desc.replace('。', '。' + chr(10)).split(chr(10)) if _s.strip()]
                _desc = _sents[-1][:200] if _sents else _desc[:100]
            if not _desc:
                _desc = '(模型未能描述图片)'
            return '[用户发了一张图片] 图片描述：' + _desc
        except Exception as _e:
            print('[message] vision API 失败: ' + str(_e))
            return content + ' (vision 分析失败)'
    return content


def extract_text_from_image(image_url):
    import os, base64, openai
    from ... import config
    try:
        fn = (image_url or '').split('/')[-1]
        if not fn:
            return None
        fp = os.path.join('uploads', fn)
        if not os.path.exists(fp):
            return None
        with open(fp, 'rb') as f:
            raw = f.read()
        low = fn.lower()
        mime = 'image/png'
        if low.endswith('.jpg') or low.endswith('.jpeg'):
            mime = 'image/jpeg'
        elif low.endswith('.gif'):
            mime = 'image/gif'
        elif low.endswith('.webp'):
            mime = 'image/webp'
        b64s = base64.b64encode(raw).decode()
        cli = openai.OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL, timeout=60)
        r = cli.chat.completions.create(
            model=config.VISION_MODEL_NAME,
            messages=[{'role': 'user', 'content': [
                {'type': 'text', 'text': '请完整提取这张图片中的所有文字内容，保留排版结构。只输出文字，不要任何说明。'},
                {'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + b64s}}
            ]}],
            max_tokens=4000
        )
        msg = r.choices[0].message
        txt = (msg.content or '').strip()
        if not txt:
            rc = getattr(msg, 'reasoning_content', None) or ''
            txt = rc.strip()
        return txt or None
    except Exception as e:
        print('[image_import] 提取失败: ' + str(e))
        return None


def import_image_to_kb(image_url, user_id):
    from .. import project_service
    txt = extract_text_from_image(image_url)
    if not txt:
        return {'success': False, 'error': '图片识别失败或未提取到文字'}
    src = '图片导入_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.md'
    try:
        n = project_service.import_document(src, 'v1.0-image', txt, user_id=user_id)
    except Exception as e:
        return {'success': False, 'error': str(e)}
    if n > 0:
        return {'success': True, 'chunks': n, 'source': src}
    return {'success': False, 'error': '图片文字重复或未新增'}




def try_handle_image_import(content, conversation_id, user_id):
    """检查 content 是否触发图片导入"""
    from ...db import db_cursor
    KW = ('图片导入知识库', '图片存入知识库', '这张图导入知识库', '把图存入知识库')
    if not any(k in content for k in KW):
        return None
    irep = ''
    try:
        with db_cursor() as cur:
            cur.execute(            "SELECT content FROM messages WHERE conversation_id=? AND content LIKE '[IMAGE]:%' ORDER BY id DESC LIMIT 1", (conversation_id,))
            fi = cur.fetchone()
        if not fi:
            irep = '未找到最近的图片，请先发一张图。'
        else:
            fc = fi['content'] if 'content' in fi.keys() else ''
            furl = fc[8:].split('|')[0].strip()
            res = import_image_to_kb(furl, user_id)
            if res.get('success'):
                irep = '已导入 ' + str(res.get('chunks', 0)) + ' 个分片（' + res.get('source', '') + '）。'
            else:
                irep = '导入失败：' + res.get('error', '未知')
    except Exception as e:
        print('[image_import] 失败: ' + str(e))
        irep = '图片导入异常：' + str(e)
    return irep
