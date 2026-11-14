import os
import httpx
# 终极绝杀：强行清空代理，强制 httpx 的底层编码为 utf-8
for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(k, None)
_orig_client = httpx.Client.__init__
def _new_client_init(self, *args, **kwargs):
    kwargs["default_encoding"] = "utf-8"
    _orig_client(self, *args, **kwargs)
httpx.Client.__init__ = _new_client_init

import os
# 强行覆盖系统环境变量，防止中文用户名导致底层网络库 ascii 报错
for k in ["USERNAME", "USERDOMAIN", "COMPUTERNAME", "HOSTNAME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEPATH", "HOMEDRIVE", "TEMP", "TMP"]:
    if k in os.environ:
        os.environ[k] = "C:\\Windows\\Temp" if k in ["TEMP", "TMP"] else "user"
os.environ["USERPROFILE"] = "C:\\Windows\\Temp"
os.environ["APPDATA"] = "C:\\Windows\\Temp"
os.environ["LOCALAPPDATA"] = "C:\\Windows\\Temp"

import os
os.environ["TEMP"] = "C:\\Windows\\Temp"
os.environ["TMP"] = "C:\\Windows\\Temp"

import sys
import locale
locale.getpreferredencoding = lambda do_setlocale=True: "utf-8"
sys.getdefaultencoding = lambda: "utf-8"
sys.getfilesystemencoding = lambda: "utf-8"

import os
import sys
import locale
for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"]:
    os.environ.pop(k, None)
os.environ["PYTHONIOENCODING"]="utf-8"
os.environ["PYTHONUTF8"]="1"
os.environ["LANG"]="en_US.UTF-8"
try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except Exception:
    pass

import os
import sys
import io
os.environ["PYTHONIOENCODING"]="utf-8"
os.environ["PYTHONUTF8"]="1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

from core.bootstrap import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
