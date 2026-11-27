"""Extract generic task context from a user's own words."""
from __future__ import annotations

import re
from pathlib import Path

PLATFORMS = {
    "youtube": ("youtube", "油管"),
    "douyin": ("douyin", "抖音"),
    "bilibili": ("bilibili", "b站", "哔哩哔哩"),
    "reddit": ("reddit",),
    "xiaohongshu": ("xiaohongshu", "小红书", "xhs"),
}
_PATH = re.compile(r"(?:[A-Za-z]:\\[^\s\"']+|(?:data|C:\\|/)[^\s\"']+\.(?:mp4|mov|png|jpg|jpeg|webp|pdf|docx|xlsx|zip))", re.I)
_URL = re.compile(r"https?://[^\s\"']+")
_CONSTRAINT_WORDS = ("不要", "不能", "必须", "先 ", "先", "禁止", "只允许", "必须人工", "dry-run", "manual", "approval")
_ACCEPT_WORDS = ("公开链接", "可访问", "验收", "完成", "回执", "发布成功")


def _artifact(path: str) -> dict:
    p = Path(path)
    if p.is_file():
        return {"id": "art_" + p.name, "type": p.suffix.lstrip(".").lower(),
                "uri": p.resolve().as_uri(), "name": p.name, "access": "local"}
    return {"id": "art_" + str(abs(hash(path)))[:10], "type": p.suffix.lstrip(".").lower(),
            "uri": path, "name": p.name, "access": "unverified"}


def extract(text: str) -> dict:
    text = str(text or "")
    low = text.lower()
    facts = []
    for platform, words in PLATFORMS.items():
        if any(w in low for w in words):
            facts.append({"key": "platform", "value": platform, "source": "user"})
            break
    artifacts = []
    for path in _PATH.findall(text):
        artifacts.append(_artifact(path))
    for url in _URL.findall(text):
        artifacts.append({"id": "art_" + str(abs(hash(url)))[:10], "type": "url",
                          "uri": url, "name": url.split("/")[-1] or "url", "access": "public"})
    constraints = [line.strip() for line in re.split(r"[。；;，,\n]", text)
                   if line.strip() and any(w in line for w in _CONSTRAINT_WORDS)]
    acceptance = [w for w in _ACCEPT_WORDS if w in text]
    return {"facts": facts, "artifacts": artifacts, "constraints": constraints,
            "acceptance": acceptance, "history_summary": ""}
