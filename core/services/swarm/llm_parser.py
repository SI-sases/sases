import asyncio
import json
from typing import Optional, List, Dict, Any
import openai
from ... import config

client = openai.OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
    timeout=180,
    max_retries=3
)

MODEL = config.MODEL_NAME

async def _call_llm(prompt: str, system_prompt: str = "", max_tokens: int = None) -> str:
    if max_tokens is None:
        max_tokens = config.COMMANDER_MAX_TOKENS
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=max_tokens,
        extra_body={"thinking": {"type": "disabled"}}
    )

    choice = resp.choices[0]
    content = choice.message.content
    finish_reason = choice.finish_reason

    print(f"[swarm-debug] finish_reason={finish_reason}, content_len={len(content) if content else 0}")

    # 优先返回 content
    if content and content.strip():
        return content.strip()

    # 兜底：从 reasoning_content 提取 JSON
    rc = getattr(choice.message, 'reasoning_content', None)
    if rc:
        print(f"[swarm-debug] content 为空，尝试从 reasoning_content 提取 JSON")
        import re as _re
        m = _re.search(r'\[\s*\{.*\}\s*\]', rc, _re.DOTALL)
        if m:
            return m.group(0)

    return ""


def _normalize_steps(steps):
    """把误写成 command 的 harness 调用自动纠正为 type=harness 格式"""
    import json as _j_norm
    out = []
    for s in (steps or []):
        if not isinstance(s, dict):
            continue
        cmd = s.get('command', '')
        if not isinstance(cmd, str):
            out.append(s)
            continue
        cmd_stripped = cmd.strip()
        handled = False
        # 情况1：command 是 JSON
        if cmd_stripped.startswith('{') and 'module_id' in cmd_stripped:
            try:
                j = _j_norm.loads(cmd_stripped)
                if isinstance(j, dict) and j.get('module_id'):
                    out.append({  'step': s.get('step'), 'type': 'harness', 'module_id': j['module_id'], 'params': j.get('params', {}), 'description': s.get('description', '') })
                    print('[_normalize] JSON command 转 harness: ' + j['module_id'])
                    handled = True
            except Exception:
                pass
        # 情况2：command 是 harness:xxx 或 harness xxx
        if not handled and ('harness:' in cmd_stripped or cmd_stripped.startswith('harness ')):
            body = cmd_stripped.replace('harness:', '', 1).replace('harness ', '', 1).strip()
            body = body.lstrip('/')
            mid = body.split(' ')[0].split(':')[0].strip()
            mid = mid.lstrip('/')
            if mid:
                out.append({  'step': s.get('step'), 'type': 'harness', 'module_id': mid, 'params': {}, 'description': s.get('description', '') })
                print('[_normalize] harness 前缀转 module_id: ' + mid)
                handled = True
        # 场景3：command 是'工具名 参数'格式，如 git_ops status
        if not handled:
            _HARNESS_NAMES = {
                'file_read', 'file_patch', 'file_copy', 'run_python',
                'grep_code', 'dir_tree', 'verify_syntax', 'verify_patch',
                'git_ops', 'api_call', 'web_fetch', 'harness_reload',
                'structure_check', 'calculator', 'unit_converter',
                'text_stats', 'json_formatter', 'base64_codec', 'string_utils',
            }
            _first = cmd_stripped.split(' ')[0].split(':')[0].strip()
            if _first in _HARNESS_NAMES:
                _rest = cmd_stripped.split(' ')[1:]
                _params = {}
                if _rest:
                    if _rest[0] in ('status', 'diff', 'add', 'push', 'pull', 'log', 'commit', 'rollback', 'snapshot', 'remote_add'):
                        _params = {'action': _rest[0]}
                        if len(_rest) > 1:
                            _params['message'] = ' '.join(_rest[1:])
                    elif _rest[0] in ('file_path', 'pattern', 'url', 'code', 'path'):
                        _params = {_rest[0]: ' '.join(_rest[1:])}
                out.append({'step': s.get('step'), 'type': 'harness', 'module_id': _first, 'params': _params, 'description': s.get('description', '')})
                print('[_normalize] command converted to harness: ' + _first)
                handled = True


        if not handled:
            out.append(s)
    return out

def _parse_plan(raw: str, max_steps: int = None) -> Optional[List[Dict[str, Any]]]:
    if not raw:
        return None
    _limit = max_steps if max_steps is not None else config.MAX_STEPS
    def _trunc(lst):
        if _limit <= 0:
            return lst
        return lst[:_limit]
    raw = raw.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            steps = json.loads(raw[start:end+1])
            if isinstance(steps, list) and steps:
                return _trunc(steps)
        except json.JSONDecodeError:
            pass

    if start != -1:
        candidate = raw[start:]
        depth = 0
        last_valid = None
        for i, ch in enumerate(candidate):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    last_valid = i
        if last_valid is not None:
            try:
                fixed = candidate[:last_valid+1] + "]"
                steps = json.loads(fixed)
                if isinstance(steps, list) and steps:
                    print(f"[swarm] _parse_plan 三级修复成功，步骤数: {len(steps)}")
                    return _trunc(steps)
            except json.JSONDecodeError:
                pass

    if start != -1:
        objects = []
        depth = 0
        obj_start = None
        for i, ch in enumerate(raw[start:], start=start):
            if ch == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    try:
                        obj = json.loads(raw[obj_start:i+1])
                        if isinstance(obj, dict) and ("command" in obj or "type" in obj):
                            objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = None
        if objects:
            for i, s in enumerate(objects):
                s["step"] = i + 1
            print(f"[swarm] _parse_plan 四级修复成功，步骤数: {len(objects)}")
            return _trunc(objects)

    return None


def _validate_steps_format(steps):
    """检查 steps 格式。返回 (valid, errors)"""
    errors = []
    valid = []
    for s in steps:
        cmd = s.get("command", "")
        if isinstance(cmd, str) and cmd.strip().lower().startswith("harness:"):
            errors.append(f"step {s.get('step')}: harness 调用写成了 command: {cmd[:50]}")
            continue
        if s.get("type") == "harness" and not s.get("module_id"):
            errors.append(f"step {s.get('step')}: type=harness 但缺 module_id")
            continue
        valid.append(s)
    return valid, errors


def _precheck_steps(steps):
    """
    执行前预检。
    返回 (warnings, blocked)：
      - warnings: 非致命问题，打印但不拦截
      - blocked: 致命问题，调用方应拦截并触发重拆
    v2.7.0 变更：
      - 返回值从 list 改为 (list, list)
      - position 不再检查（信任 file_patch 的归一化）
      - run_python 的 import 检查更新为真正的禁用模块
    """
    warnings = []
    blocked = []
    for s in steps:
        module_id = s.get("module_id", "")
        params = s.get("params", {}) or {}
        step_num = s.get("step", "?")
        if module_id == "file_patch":
            fp = params.get("file_path", "")
            _has_placeholder = False
            for _k in ('old_snippet', 'new_content', 'anchor_pattern', 'file_path'):
                _v = params.get(_k, '')
                if isinstance(_v, str) and ('{{step' in _v or '{step' in _v):
                    _has_placeholder = True
                    break
            
            # 检查前面是否有读文件操作，如果有，允许参数为空，推迟到执行后再补全
            _has_prior_read = any(
                (prev.get('module_id') == 'file_read' and prev.get('params', {}).get('file_path') == fp)
                for prev in steps if prev.get('step', 0) < step_num
            )
            
            if not _has_placeholder and not _has_prior_read:
                if not params.get("anchor_pattern") and not params.get("old_snippet") and not params.get("new_content"):
                    blocked.append(f"step {step_num}: file_patch 缺参数且无前置读取")
            if "file_patch/main.py" in fp or "executor_service.py" in fp:
                blocked.append(f"step {step_num}: 目标是受保护文件")
        if module_id == "file_read":
            fp = params.get("file_path", "")
            if "{{step" in fp or "{step" in fp:
                blocked.append(f"step {step_num}: 路径含未替换占位符")
        if module_id == "run_python":
            code = params.get("code", "")
            for banned in ("subprocess", "socket", "ctypes", "multiprocessing", "signal"):
                if f"import {banned}" in code:
                    warnings.append(f"step {step_num}: run_python 含 import {banned}")
                    break
    return warnings, blocked
