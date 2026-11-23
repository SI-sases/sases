"""Fail CI when a t('key') is missing from zh/en dictionaries.

Catches keys that were never added to either dictionary, which the
zh-vs-en comparison cannot see.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "modules")


def keys(path):
    with open(path, encoding="utf-8") as f:
        return set(re.findall(r"'([^']+)'\s*:", f.read()))


def main():
    zh = keys(os.path.join(ROOT, "i18n_zh.js"))
    en = keys(os.path.join(ROOT, "i18n_en.js"))
    used = {}
    for name in os.listdir(ROOT):
        if not name.endswith(".js") or name in ("i18n_zh.js", "i18n_en.js", "pinyin-pro.js"):
            continue
        with open(os.path.join(ROOT, name), encoding="utf-8", errors="ignore") as f:
            for key in re.findall(r"\bt\(\s*'([^']+)'\s*\)", f.read()):
                used.setdefault(key, set()).add(name)
    missing_zh = sorted(k for k in used if k not in zh)
    missing_en = sorted(k for k in used if k not in en)
    if missing_zh or missing_en:
        for key in missing_zh:
            print(f"MISSING zh: {key} used by {sorted(used[key])[:3]}")
        for key in missing_en:
            print(f"MISSING en: {key} used by {sorted(used[key])[:3]}")
        return 1
    print(f"i18n usage ok: {len(used)} used keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
