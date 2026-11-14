import shutil
from datetime import datetime

INIT = "core/api_routes/__init__.py"
BOOT = "core/bootstrap.py"

def main():
    # 1. __init__.py 加 from . import scheduled_routes
    c = open(INIT, "r", encoding="utf-8").read()
    if "scheduled_routes" not in c:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(INIT, INIT + ".bak_p2_6_" + ts)
        anchor = "from . import hive_task_routes"
        if anchor in c:
            c = c.replace(anchor, anchor + "\nfrom . import scheduled_routes", 1)
            open(INIT, "w", encoding="utf-8").write(c)
            print("__init__.py: import added")
        else:
            print("ERROR: init anchor not found")
    else:
        print("__init__.py: already mounted")

    # 2. bootstrap.py 加 include_router
    c = open(BOOT, "r", encoding="utf-8").read()
    if "scheduled_routes" not in c:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(BOOT, BOOT + ".bak_p2_6_" + ts)
        anchor = "app.include_router(group_routes.router)"
        if anchor in c:
            c = c.replace(anchor, anchor + "\n    app.include_router(scheduled_routes.router)", 1)
            # 同时确保 import 里有 scheduled_routes
            if "scheduled_routes" not in c.split("app.include_router(scheduled_routes.router)")[0]:
                import_anchor = "group_routes,"
                if import_anchor in c:
                    c = c.replace(import_anchor, import_anchor + "\n    scheduled_routes,", 1)
            open(BOOT, "w", encoding="utf-8").write(c)
            print("bootstrap.py: router mounted")
        else:
            print("ERROR: bootstrap anchor not found")
    else:
        print("bootstrap.py: already mounted")

if __name__ == "__main__":
    main()