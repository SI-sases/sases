import ctypes
import time

user32 = ctypes.windll.user32


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

_DOWN = {"left": 0x0002, "right": 0x0008, "middle": 0x0020}
_UP = {"left": 0x0004, "right": 0x0010, "middle": 0x0040}


def _screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)



def _focus_window(title):
    if not title:
        return None
    title = str(title)
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _):
        try:
            length = user32.GetWindowTextLengthW(hwnd)
            if not length:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if title.lower() in buf.value.lower() and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
                return False
        except Exception:
            pass
        return True

    user32.EnumWindows(enum_proc, 0)
    if not found:
        return None
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)
    try:
        user32.SwitchToThisWindow(hwnd, True)
    except Exception:
        pass
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.35)
    if user32.GetForegroundWindow() == hwnd:
        return hwnd
    return None


def _uia_click(name, window_title=""):
    import base64
    import subprocess
    safe_name = str(name).replace("'", "''")
    safe_title = str(window_title or "").replace("'", "''")
    script = f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$name = '{safe_name}'
$title = '{safe_title}'
$root = [System.Windows.Automation.AutomationElement]::RootElement
$scope = [System.Windows.Automation.TreeScope]::Descendants
$window = $root
if ($title -ne '') {{
  $wc = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $title)
  $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $wc)
}}
if ($null -eq $window) {{ Write-Output 'NO_WINDOW'; exit 2 }}
$cond = New-Object System.Windows.Automation.AndCondition(
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)),
  (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $name))
)
$el = $window.FindFirst($scope, $cond)
if ($null -eq $el) {{
  $bc = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
  $list = $window.FindAll($scope, $bc)
  if ($list.Count -eq 1) {{ $el = $list.Item(0) }} else {{ Write-Output "NO_BUTTON count=$($list.Count)"; exit 3 }}
}}
$pattern = $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
$pattern.Invoke()
Write-Output 'INVOKED'
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        capture_output=True, text=True, timeout=15,
    )
    return proc.returncode == 0 and "INVOKED" in (proc.stdout or "")

def run(params):
    enable_dpi_awareness()
    x = int(params.get("x"))
    y = int(params.get("y"))
    width, height = _screen_size()
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(f"坐标超出屏幕范围: ({x},{y}) / {width}x{height}")

    button = str(params.get("button") or "left").lower()
    if button not in _DOWN:
        raise ValueError("button must be left/right/middle")
    clicks = max(1, min(int(params.get("clicks") or 1), 3))
    interval = max(0.0, min(float(params.get("interval") or 0.15), 2.0))
    confirm = bool(params.get("confirm"))
    move_only = bool(params.get("move_only"))

    hwnd = _focus_window(params.get("window_title"))
    if params.get("window_title") and not hwnd:
        # First click activates the window; second click presses the control.
        clicks = max(clicks, 2)
    result = {"x": x, "y": y, "button": button, "clicks": clicks, "screen": [width, height], "focused_window": bool(hwnd)}
    uia_name = params.get("uia_name")
    if uia_name:
        ok = _uia_click(uia_name, params.get("window_title"))
        result.update({"uia": True, "executed": bool(ok), "uia_name": uia_name})
        return result
    if not confirm:
        result.update({"executed": False, "dry_run": True, "reason": "pass confirm=true to execute"})
        return result

    user32.SetCursorPos(x, y)
    time.sleep(0.05)
    if move_only:
        result["executed"] = True
        return result

    for index in range(clicks):
        user32.mouse_event(_DOWN[button], 0, 0, 0, 0)
        user32.mouse_event(_UP[button], 0, 0, 0, 0)
        if index + 1 < clicks:
            time.sleep(interval)
    result["executed"] = True
    return result
