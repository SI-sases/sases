"""Main AGI conversational facade.

It is intentionally a small intent router, not a second LLM: the main AGI's
job is to call tools and report, not to invent facts.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import support
from .report import generate


def _has(text: str, *words: str) -> bool:
    return any(w in text for w in words)


def answer(text: str, db_path: str = "data/agi.db", observe=None) -> dict:
    text = (text or "").strip()
    if not text:
        return {"markdown": "## 需要指令\n\n请告诉我要检查什么。", "intent": "empty"}

    if _has(text, "发布", "发帖", "提交", "上传"):
        return {
            "intent": "publish",
            "markdown": (
                "## 发布请求\n\n"
                "我可以执行，但需要先确认：\n\n"
                "- 平台\n- 账号\n- 标题和正文\n- 是否已经 dry-run\n\n"
                "**不会直接提交未经确认的内容。**"
            ),
        }

    if _has(text, "客服", "工单", "退款", "怎么安装", "打不开", "登录"):
        draft = support.draft_reply(text)
        lines = ["## 客服判断", "", "**分类**：" + support.classify(text)["category"]]
        if draft["needs_human"]:
            lines += ["", "这个问题需要人工处理：**退款/法律/安全/账号**。", "", "已建议升级。"]
        elif draft["answer"]:
            lines += ["", draft["answer"], "", "来源：" + "、".join(draft["sources"])]
        else:
            lines += ["", "知识库没有命中，建议建工单。"]
        return {"intent": "support", "markdown": "\n".join(lines)}

    if _has(text, "状态", "检查", "汇报", "健康", "怎么样", "情况"):
        if observe:
            try:
                observe()
            except Exception:
                pass
        report = generate(db_path)
        return {"intent": "status", "markdown": report}

    if _has(text, "需要我", "异常", "故障", "处理", "升级"):
        report = generate(db_path)
        return {"intent": "escalation", "markdown": report}

    return {
        "intent": "fallback",
        "markdown": (
            "## 我听到了\n\n"
            "当前可以处理：\n\n"
            "- 节点状态\n- 客服工单\n- 发布 dry-run\n- 任务回执\n\n"
            "请补充平台、任务或具体问题。"
        ),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--db", default="data/agi.db")
    args = parser.parse_args()
    print(json.dumps(answer(args.text, args.db), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
