"""User-facing content policy.

Do not add vendor-affiliation disclaimers to future posts. If old content
contains them, strip them before sending to a platform.
"""
from __future__ import annotations

import re

BANNED = (
    "非大厂官方产品",
    "独立开源项目",
    "不是任何大厂",
    "非大厂",
    "大厂官方",
    "大厂旗下",
    "big-vendor product",
    "not a big-vendor",
    "not affiliated with a big vendor",
)


def sanitize(text: str) -> str:
    out = str(text or "")
    for phrase in BANNED:
        out = re.sub(re.escape(phrase), "", out, flags=re.I)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
