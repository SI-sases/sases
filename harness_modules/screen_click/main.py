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

    result = {"x": x, "y": y, "button": button, "clicks": clicks, "screen": [width, height]}
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
