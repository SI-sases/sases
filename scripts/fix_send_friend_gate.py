# scripts/fix_send_friend_gate.py
import os

TARGET = "core/services/message/send.py"

def main():
    if not os.path.exists(TARGET):
        print("找不到 send.py")
        return

    content = open(TARGET, "r", encoding="utf-8").read()

    # 1. 导入 friend_gate
    import_stmt = "from ..friend_gate import check_friend_gate"
    if import_stmt not in content:
        # 寻找已有的 db_cursor 导入并加在后面
        anchor = "from ...db import db_cursor"
        if anchor in content:
            content = content.replace(anchor, anchor + "\n" + import_stmt, 1)
            print("✅ friend_gate 导入已添加")
        else:
            # 兜底，直接加在文件最前面（第一行 import 之后）
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    lines.insert(i + 1, import_stmt)
                    break
            content = "\n".join(lines)
            print("✅ friend_gate 导入已添加 (文件头)")

    # 2. 拦截逻辑注入
    if "check_friend_gate(user_id" not in content:
        # 在函数的最开头（通常是第一个 _scan_content 附近）插入
        anchor = "_scan_content = _normalize_prefix(content)"
        if anchor in content:
            gate_logic = """_gate = check_friend_gate(user_id, conversation_id, sender_agent_id, content, agent_id, mode)
    if _gate.get("action") == "block":
        return {
            'conversation_id': conversation_id,
            'user_message': content,
            'assistant_reply': _gate["reply"],
            'agent_id': agent_id,
            'sender_agent_id': sender_agent_id,
            'mode': mode,
        }

    """
            content = content.replace(anchor, gate_logic + anchor, 1)
            print("✅ 拦截逻辑已注入")
        else:
            print("❌ 找不到 _scan_content 锚点，无法插入拦截逻辑")
    else:
        print("✅ 拦截逻辑已存在")

    open(TARGET, "w", encoding="utf-8").write(content)
    print("🎉 修复脚本执行完毕")

if __name__ == "__main__":
    main()