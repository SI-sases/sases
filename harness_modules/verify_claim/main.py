import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKSLASH = chr(92)


def _safe(path):
    if not path:
        return None
    p = path.replace(BACKSLASH, '/').strip()
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        return None
    if '..' in p.split('/'):
        return None
    return p


def run(params):
    source = params.get('source_file', '').strip()
    claim = params.get('claim', '').strip()
    if not source or not claim:
        return {'success': False, 'error': 'need source_file and claim'}
    safe = _safe(source)
    if not safe:
        return {'success': False, 'error': 'invalid source_file'}
    abs_path = os.path.join(REPO_ROOT, safe)
    if not os.path.exists(abs_path):
        return {'success': False, 'error': 'file not found: ' + safe}
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return {'success': False, 'error': str(e)}
    claim_stripped = claim.strip()
    hits = []
    for ln, line in enumerate(lines, 1):
        if claim_stripped in line:
            hits.append({'line': ln, 'text': line.rstrip()[:200]})
    if hits:
        return {'success': True, 'source_file': safe, 'claim': claim[:100], 'verified': True, 'match_mode': 'exact', 'hits': hits[:10], 'total_hits': len(hits)}
    claim_norm = re.sub(r'\s+', '', claim_stripped).lower()
    fuzzy = []
    for ln, line in enumerate(lines, 1):
        line_norm = re.sub(r'\s+', '', line).lower()
        if claim_norm and claim_norm in line_norm:
            fuzzy.append({'line': ln, 'text': line.rstrip()[:200]})
    if fuzzy:
        return {'success': True, 'source_file': safe, 'claim': claim[:100], 'verified': True, 'match_mode': 'fuzzy', 'hits': fuzzy[:10], 'total_hits': len(fuzzy)}
    return {'success': True, 'source_file': safe, 'claim': claim[:100], 'verified': False, 'message': 'not found in source', 'total_lines': len(lines)}
