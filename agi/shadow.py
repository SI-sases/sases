"""Compare an expected playbook with an observed trace.

P3 uses this offline before enabling any auto-remediation.
"""
from __future__ import annotations


def compare_steps(expected: list[str], observed: list[str]) -> dict:
    exp = list(expected)
    obs = list(observed)
    matched = 0
    j = 0
    for step in exp:
        try:
            idx = obs.index(step, j)
        except ValueError:
            continue
        matched += 1
        j = idx + 1
    missing = [s for s in exp if s not in obs]
    extra = [s for s in obs if s not in exp]
    return {
        "expected": exp,
        "observed": obs,
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "coverage": round(matched / len(exp), 3) if exp else 1.0,
    }
