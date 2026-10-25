import os
import re
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, 'harness_modules')

PARAM_PATTERN = re.compile(r"params\.get\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*(.+?))?\)")

_OVERRIDE_REQUIRED = {
    'grep_code': ['pattern'],
    'api_call': ['url'],
    'web_fetch': ['url'],
    'compare_texts': ['a', 'b'],
    'calculator': ['expression'],
    'verify_claim': ['source_file', 'claim'],
    'verify_syntax': ['file_path'],
    'verify_patch': ['file_path'],
    'answer': ['content'],
    'file_replace_range': ['file_path', 'start_line', 'end_line'],
    'file_copy': ['src', 'dst'],
    'run_python': ['code'],
    'file_read': ['file_path'],
    'file_patch': ['file_path'],
    'git_ops': ['action'],
    'structure_check': ['file_path'],
    'text_stats': ['text'],
    'string_utils': ['operation', 'text'],
    'base64_codec': ['action', 'text'],
    'json_formatter': ['json_string'],
    'verify_ui': ['action'],
}

_OVERRIDE_OPTIONAL = {
    'api_call': ['method', 'headers', 'body'],
    'file_copy': ['src_path', 'dst_path', 'overwrite'],
    'extract_keypoints': ['source_file', 'text', 'max'],
    'read_user_doc': ['source_file', 'user_id'],
    'dir_tree': ['path', 'max_depth'],
    'file_read': ['lines', 'grep', 'max_results', 'max_lines', 'offset'],
    'file_patch': ['old_snippet', 'new_snippet', 'expected_count', 'anchor_pattern', 'position', 'new_content', 'create_if_missing', 'overwrite'],
    'git_ops': ['n', 'file', 'message', 'branch', 'remote', 'steps', 'name', 'url'],
    'verify_syntax': ['check_undefined', 'auto_rollback'],
    'verify_patch': ['expect_contains', 'expect_not_contains'],
    'verify_ui': ['url', 'timeout', 'filename', 'selector'],
    'file_replace_range': ['new_content'],
}


def _infer_type(default_repr):
    if not default_repr:
        return 'any'
    d = default_repr.strip()
    if d.startswith('['):
        return 'array'
    if d.startswith('{') or d.startswith('dict('):
        return 'object'
    if d in ('True', 'False'):
        return 'bool'
    if d in ('None',):
        return 'any'
    if d.startswith('int(') or (d and d[0].isdigit()):
        return 'int'
    if d.startswith('float('):
        return 'float'
    if d.startswith('\"') or d.startswith("'"):
        return 'string'
    return 'any'


def _clean_default(default_repr):
    if not default_repr:
        return None
    d = default_repr.strip()
    if d in ('None',):
        return None
    try:
        return eval(d, {'__builtins__': {}}, {})
    except Exception:
        return d.strip('\"\'')


def main():
    updated = 0
    for module_name in sorted(os.listdir(HARNESS_DIR)):
        module_path = os.path.join(HARNESS_DIR, module_name)
        if not os.path.isdir(module_path):
            continue
        main_py = os.path.join(module_path, 'main.py')
        manifest_json = os.path.join(module_path, 'manifest.json')
        if not os.path.exists(main_py) or not os.path.exists(manifest_json):
            continue
        try:
            with open(main_py, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception:
            continue
        matches = PARAM_PATTERN.findall(code)
        if not matches:
            continue
        params_schema = {}
        _req_list = _OVERRIDE_REQUIRED.get(module_name, [])
        _opt_list = _OVERRIDE_OPTIONAL.get(module_name, [])
        for name, default in matches:
            if name in params_schema:
                continue
            entry = {'type': _infer_type(default)}
            if name in _opt_list:
                if default:
                    cd = _clean_default(default)
                    if cd is not None:
                        entry['default'] = cd
                entry['desc'] = '可选'
            elif name in _req_list:
                entry['desc'] = '必填'
            elif default:
                cd = _clean_default(default)
                if cd is not None:
                    entry['default'] = cd
                    entry['desc'] = '可选'
                else:
                    entry['desc'] = '必填'
            else:
                entry['desc'] = '必填'
            params_schema[name] = entry
        try:
            with open(manifest_json, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception:
            continue
        if manifest.get('params') == params_schema:
            continue
        manifest['params'] = params_schema
        try:
            with open(manifest_json, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            updated += 1
            print(f'updated: {module_name} -> {list(params_schema.keys())}')
        except Exception as e:
            print(f'failed: {module_name}: {e}')
    print(f'\n\u5171\u66f4\u65b0 {updated} \u4e2a\u6a21\u5757')


if __name__ == '__main__':
    main()
