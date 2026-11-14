import shutil
from datetime import datetime

TARGET = "core/bootstrap.py"

def main():
    content = open(TARGET, "r", encoding="utf-8").read()

    if "scheduled_task_scheduler" in content:
        print("already mounted, skip")
        return

    anchor = "_background_tasks.append(asyncio.create_task(periodic_hlc_health()))"
    if anchor not in content:
        print("ERROR: anchor not found")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TARGET, TARGET + ".bak_p2_6_" + ts)
    print("backup done")

    new_line = anchor + "\n    _background_tasks.append(asyncio.create_task(scheduled_task_scheduler()))"
    content = content.replace(anchor, new_line, 1)

    import_anchor = "from .services import state_service as _state_svc"
    if import_anchor in content:
        content = content.replace(import_anchor, import_anchor + "\n    from .services.scheduled_scheduler import scheduled_task_scheduler", 1)
    else:
        # 兜底：在 lifespan 函数开头加
        content = content.replace("async def lifespan(app: FastAPI):", "async def lifespan(app: FastAPI):\n    from .services.scheduled_scheduler import scheduled_task_scheduler", 1)

    open(TARGET, "w", encoding="utf-8").write(content)
    print("mounted")

if __name__ == "__main__":
    main()