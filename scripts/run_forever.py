# scripts/run_forever.py
import os
import sys

# ⚠️ 客户端默认禁用本地 embedding（避免 onnxruntime native 崩溃）
if os.environ.get("SASES_ENABLE_LOCAL_EMBEDDING") != "1":
    os.environ["SASES_DISABLE_LOCAL_EMBEDDING"] = "1"
    print("[wrapper] 本地 embedding 已禁用，走 API 模式", flush=True)

# 强制把解压根目录加入 sys.path，切换工作目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

print(f"[wrapper] root={ROOT}", flush=True)
print(f"[wrapper] python={sys.executable}", flush=True)
print(f"[wrapper] cwd={os.getcwd()}", flush=True)

import uvicorn

PORT = int(os.environ.get("SASES_PORT", "8001"))
HOST = os.environ.get("SASES_HOST", "0.0.0.0")

print(f"[wrapper] starting uvicorn on {HOST}:{PORT}", flush=True)

if __name__ == "__main__":
    uvicorn.run(
        "app_full:app",
        host=HOST,
        port=PORT,
        log_level="info",
        access_log=False,
    )
