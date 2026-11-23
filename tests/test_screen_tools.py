import os

import pytest

from core.harness_loader import load_harness_modules


def _modules():
    return load_harness_modules("harness_modules")


def test_screen_modules_are_registered():
    modules = _modules()
    assert "screen_capture" in modules
    assert "screen_click" in modules
    assert "screen_vision" in modules


def test_screen_click_is_dry_run_by_default():
    modules = _modules()
    result = modules["screen_click"]["run_fn"]({"x": 10, "y": 10})
    assert result["executed"] is False
    assert result["dry_run"] is True


def test_screen_click_rejects_out_of_bounds():
    modules = _modules()
    with pytest.raises(ValueError):
        modules["screen_click"]["run_fn"]({"x": 99999, "y": 99999, "confirm": True})


def test_screen_capture_returns_image(tmp_path):
    modules = _modules()
    try:
        result = modules["screen_capture"]["run_fn"]({
            "save_path": str(tmp_path / "screen.png"),
            "scale": 0.2,
        })
    except Exception as exc:
        pytest.skip(f"no interactive desktop: {exc}")
    assert os.path.isfile(result["path"])
    assert result["width"] > 0 and result["height"] > 0
