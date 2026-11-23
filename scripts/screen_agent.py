#!/usr/bin/env python3
"""Minimal, testable screen agent: screenshot -> vision -> click -> verify.

Examples:
  python scripts/screen_agent.py --goal "点击登录按钮" --confirm
  python scripts/screen_agent.py --goal "找到设置按钮"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.harness_loader import load_harness_modules


def _parse_json(text: str) -> dict:
    fenced = re.search(r"\{.*\}", text, re.S)
    if not fenced:
        raise ValueError("vision response has no JSON object")
    return json.loads(fenced.group(0))


def _pick_element(data: dict, goal: str) -> dict | None:
    elements = data.get("elements") or []
    if isinstance(data.get("target"), dict):
        elements = [data["target"]] + elements
    if data.get("x") is not None and data.get("y") is not None:
        elements = [data] + elements
    if not elements:
        return None
    goal_low = goal.lower()
    for item in elements:
        label = str(item.get("label", "")).lower()
        if label and (label in goal_low or goal_low in label):
            return item
    return elements[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", required=True)
    parser.add_argument("--confirm", action="store_true", help="actually click; default dry-run")
    parser.add_argument("--verify", action="store_true", help="screenshot after click and ask vision to verify")
    parser.add_argument("--out", default=os.path.join(ROOT, "data", "screenshots"))
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    modules = load_harness_modules(os.path.join(ROOT, "harness_modules"))
    before = os.path.join(args.out, "agent_before.png")
    shot = modules["screen_capture"]["run_fn"]({"save_path": before})
    print("screenshot", json.dumps(shot, ensure_ascii=False))

    prompt = (
        f"你是屏幕操作助手。目标：{args.goal}。"
        "只输出 JSON："
        '{"summary":"画面说明","found":true,"label":"目标控件","x":123,"y":456}。'
        "x/y 必须是截图像素坐标，指向控件中心；找不到则 found=false。"
    )
    vision = modules["screen_vision"]["run_fn"]({
        "image_path": before,
        "prompt": prompt,
        "model": os.environ.get("SASES_VISION_MODEL") or None,
    })
    print("vision", vision.get("answer", "")[:500])
    data = _parse_json(vision["answer"])
    target = _pick_element(data, args.goal)
    if not target or data.get("found") is False:
        print("not-found", json.dumps(data, ensure_ascii=False))
        return 2

    if target.get("x_norm") is not None and target.get("y_norm") is not None:
        x = int(float(target["x_norm"]) * shot["width"])
        y = int(float(target["y_norm"]) * shot["height"])
    else:
        x, y = int(target["x"]), int(target["y"])
    click = modules["screen_click"]["run_fn"]({
        "x": x, "y": y, "confirm": bool(args.confirm), "button": "left", "clicks": 1,
    })
    print("click", json.dumps(click, ensure_ascii=False))
    if not args.confirm:
        print("dry-run: pass --confirm to execute")
        return 0

    time.sleep(1.0)
    after = os.path.join(args.out, "agent_after.png")
    modules["screen_capture"]["run_fn"]({"save_path": after})
    if args.verify:
        check = modules["screen_vision"]["run_fn"]({
            "image_path": after,
            "prompt": f"刚才点击了「{args.goal}」。请判断是否成功，只回答 成功 或 失败，并说明画面变化。",
        })
        print("verify", check.get("answer", "")[:500])
    print("after", after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
