# core/services/swarm/tool_output.py
# -*- coding: utf-8 -*-
"""D: 工具输出的幂等、脱敏包裹、大输出落盘。"""
import os

MAX_OUTPUT_LENGTH = 20000
SIDE_EFFECT = {"file_write", "smart_edit", "file_replace_range", "delete_block",
               "split_block", "git_ops", "http_async"}
UNTRUSTED_TOOLS = {"web_fetch", "api_call", "http_async", "read_user_doc"}


def wrap_untrusted(tool_id: str, text) -> str:
    if tool_id not in UNTRUSTED_TOOLS:
        return text
    return ('<untrusted_tool_output tool="' + str(tool_id) + '">\n'
            + str(text) + '\n</untrusted_tool_output>')


def idem_put(module_id: str, key, output):
    if not key or module_id not in SIDE_EFFECT:
        return
    try:
        from .. import run_journal as _rj
        _rj.effect_put(str(key), module_id, str(output)[:20000])
    except Exception as e:
        print("[idempotent] 写入失败: " + str(e))


def spill_large(output, run_id=None, conversation_id=None, user_id=None, module_id="tool"):
    """超过 MAX_OUTPUT_LENGTH 的输出落 artifact，返回截断文本 + 指针。"""
    text = str(output or "")
    if len(text) <= MAX_OUTPUT_LENGTH:
        return text
    try:
        import time as _time
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        _dir = os.path.join(_root, "static", "generated")
        os.makedirs(_dir, exist_ok=True)
        _name = "tool_output_" + str(run_id or 0) + "_" + str(int(_time.time() * 1000)) + ".txt"
        _path = os.path.join(_dir, _name)
        with open(_path, "w", encoding="utf-8") as f:
            f.write(text)
        _url = "/static/generated/" + _name
        try:
            from .. import artifact_service
            artifact_service.record(run_id, conversation_id, user_id, _url,
                                    kind="file", name=_name,
                                    meta={"tool": module_id, "kind": "tool_output"}, silent=True)
        except Exception as e:
            print("[artifact] 记录大输出失败: " + str(e))
        print("[artifact] 大输出已落盘 " + _url + " (" + str(len(text)) + " chars)")
        return text[:MAX_OUTPUT_LENGTH] + "\n...[已截断，完整输出: " + _url + "]"
    except Exception as e:
        print("[artifact] 大输出落盘失败: " + str(e))
        return text[:MAX_OUTPUT_LENGTH]
