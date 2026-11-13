# scripts/refactor_group_at_agent_v2.py
import shutil
from datetime import datetime

ROUTES = "core/api_routes/group_routes.py"
SERVICE = "core/services/group_service.py"

# 精确范围：原行号 125-162（函数体 + 2 个尾随空行）
# Python 列表索引：[124:162]
START_IDX = 124
END_IDX = 162

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(ROUTES, ROUTES + ".bak_v2_" + ts)
    shutil.copy2(SERVICE, SERVICE + ".bak_v2_" + ts)
    print("backup done")

    routes_lines = open(ROUTES, "r", encoding="utf-8").read().split("\n")
    service_content = open(SERVICE, "r", encoding="utf-8").read()

    if "async def handle_at_agent" in service_content:
        print("already patched, skip")
        return

    # 提取 125-162 行（索引 124:162）
    func_lines = routes_lines[START_IDX:END_IDX]
    func_code = "\n".join(func_lines)

    if "async def _handle_at_agent" not in func_code:
        print("ERROR: 提取范围不对")
        print("前 3 行:", func_lines[:3])
        print("后 3 行:", func_lines[-3:])
        return

    # 改造函数
    modified = func_code
    modified = modified.replace(
        "from ..services import group_service, group_resource_service",
        "from . import group_resource_service"
    )
    modified = modified.replace("    from ..db import db_cursor\n", "")
    modified = modified.replace("group_service.parse_at_prefix", "parse_at_prefix")
    modified = modified.replace("group_service._is_human_in_group", "_is_human_in_group")
    modified = modified.replace("group_service._find_agent_id_by_name", "_find_agent_id_by_name")
    modified = modified.replace("group_service.insert_agent_message", "insert_agent_message")
    modified = modified.replace("from .ws_routes import broadcast_to_group",
                                "from ..api_routes.ws_routes import broadcast_to_group")
    modified = modified.replace("async def _handle_at_agent", "async def handle_at_agent", 1)

    # 追加到 group_service.py
    new_service = service_content.rstrip() + "\n\n\n" + modified + "\n"
    open(SERVICE, "w", encoding="utf-8").write(new_service)
    print("appended handle_at_agent")

    # 从 group_routes.py 删除 125-162
    new_routes_lines = routes_lines[:START_IDX] + routes_lines[END_IDX:]
    new_routes_content = "\n".join(new_routes_lines)
    new_routes_content = new_routes_content.replace(
        "_aio.create_task(_handle_at_agent(group_id, user_id, body.content))",
        "_aio.create_task(group_service.handle_at_agent(group_id, user_id, body.content))"
    )
    open(ROUTES, "w", encoding="utf-8").write(new_routes_content)
    print("removed _handle_at_agent from routes")
    print("DONE")

if __name__ == "__main__":
    main()