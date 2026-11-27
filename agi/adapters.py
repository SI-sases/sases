"""Platform adapter contract.

Each platform has its own login/session, selectors and rules.  Adapters are
explicitly registered; a platform without an adapter is not silently treated as
supported.
"""
from __future__ import annotations

from typing import Any, Callable

Runner = Callable[[dict[str, Any]], dict[str, Any]]


class Adapter:
    def __init__(self, adapter_id: str, mode: str, runner: Runner | None = None,
                 reason: str = "") -> None:
        self.id = adapter_id
        self.mode = mode
        self.runner = runner
        self.reason = reason

    def run(self, args: dict[str, Any]) -> dict[str, Any]:
        if self.runner is None:
            return {"ok": False, "adapter": self.id, "error": "adapter_not_implemented",
                    "reason": self.reason or "not implemented"}
        result = self.runner(args)
        result.setdefault("adapter", self.id)
        return result

    def info(self) -> dict:
        return {"id": self.id, "mode": self.mode, "implemented": self.runner is not None,
                "reason": self.reason}


def _reddit(args: dict[str, Any]) -> dict[str, Any]:
    from .browser import reddit_post
    return reddit_post(args)


def _douyin(args: dict[str, Any]) -> dict[str, Any]:
    from .browser import douyin_post
    return douyin_post(args)


def _bilibili(args: dict[str, Any]) -> dict[str, Any]:
    from .browser import bilibili_post
    return bilibili_post(args)


def registry() -> dict[str, Adapter]:
    return {
        "reddit": Adapter("reddit", "approval", _reddit),
        "douyin": Adapter("douyin", "approval", _douyin),
        "bilibili": Adapter("bilibili", "approval", _bilibili),
        "youtube": Adapter("youtube", "planned", reason="video upload adapter not implemented"),
        "xiaohongshu": Adapter("xiaohongshu", "manual",
                               reason="platform risk warning; manual-only"),
    }


def list_adapters() -> list[dict]:
    return [adapter.info() for adapter in registry().values()]


def run(adapter_id: str, args: dict[str, Any]) -> dict[str, Any]:
    adapter = registry().get(adapter_id)
    if not adapter:
        return {"ok": False, "error": "unknown_adapter", "adapter": adapter_id}
    return adapter.run(args)
