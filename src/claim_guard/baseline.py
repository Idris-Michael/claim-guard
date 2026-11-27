"""The guard this project replaces, ported line for line so the benchmark compares like with like.

It finds claims with four regexes and lets one through when the claim's text, lower-cased with
spaces removed, appears anywhere in the verified source. Kept only as a baseline.
"""

from __future__ import annotations

import re

PLACEHOLDER = "[PROOF POINT: verified metric required]"

_PATTERNS = [
    re.compile(r"[+\-]?\d+(?:\.\d+)?\s?%"),
    re.compile(r"\b\d+(?:\.\d+)?\s?[x×](?![\w\d])"),
    re.compile(r"\bROAS\s+(?:of\s+)?\d+(?:\.\d+)?[x×]?", re.I),
    re.compile(
        r"[+]?£\s?\d[\d,.]*\s?[km]?\s+(?:in\s+)?(?:extra\s+|additional\s+|new\s+)?"
        r"(?:revenue|sales|profit|savings|saved|pipeline)\b",
        re.I,
    ),
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())


def baseline_guard(draft: str, verified: str) -> tuple[str, list[str]]:
    """Return the guarded text and the claims it removed."""
    vnorm = _norm(verified)
    removed: list[str] = []
    out = draft

    def repl(m: re.Match[str]) -> str:
        if vnorm and _norm(m.group(0)) in vnorm:
            return m.group(0)
        removed.append(m.group(0).strip())
        return PLACEHOLDER

    for rx in _PATTERNS:
        out = rx.sub(repl, out)
    return out, removed
