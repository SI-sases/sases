"""Bounded context compaction for long tool results."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _dir() -> Path:
    return Path(os.environ.get("SASES_CONTEXT_DIR", "data/context"))


def compact_text(text: str, max_head: int = 4000, max_tail: int = 1000) -> dict:
    raw = str(text or "")
    if len(raw) <= max_head + max_tail:
        return {"ok": True, "text": raw, "compacted": False, "chars": len(raw)}
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    target = _dir() / (digest + ".txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(raw, encoding="utf-8")
    return {"ok": True, "compacted": True, "chars": len(raw),
            "head": raw[:max_head], "tail": raw[-max_tail:],
            "artifact": str(target), "sha256": digest}


def compact_result(result: dict, threshold: int = 12000) -> dict:
    try:
        raw = json.dumps(result, ensure_ascii=False)
    except Exception:
        return result
    if len(raw) <= threshold:
        return result
    out = dict(result)
    out["summary"] = "result compacted; full output saved as artifact"
    out["artifact"] = compact_text(raw)["artifact"]
    out["original_chars"] = len(raw)
    for key in ("text", "output", "data"):
        if key in out:
            out[key] = str(out[key])[:2000]
    return out
