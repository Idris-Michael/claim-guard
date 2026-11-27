"""Find result-style claims in text and reduce each one to a comparable (kind, value) key.

A claim is a number that states an outcome: a percentage, a multiplier, a money result or a
count of results ("1,200 new leads"). Prices, dates, versions and team sizes are not results and
are never returned, so the guard cannot mangle them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Words that name what a number measures. Used to tell "40% lower cost" from "40% more sales".
METRIC_WORDS = frozenset(
    [
        "roas",
        "roi",
        "revenue",
        "sales",
        "profit",
        "savings",
        "saved",
        "pipeline",
        "conversion",
        "conversions",
        "cpa",
        "cpl",
        "cpc",
        "ctr",
        "cost",
        "costs",
        "leads",
        "lead",
        "traffic",
        "sessions",
        "bookings",
        "orders",
        "signups",
        "sign-ups",
        "customers",
        "clients",
        "retention",
        "churn",
        "engagement",
        "reach",
        "impressions",
        "spend",
        "margin",
        "aov",
        "basket",
        # added after run 1: verified facts about these were rejected for having no metric word
        "enquiries",
        "inquiries",
        "demos",
    ]
)

_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_CURRENCY = {"£": "GBP", "$": "USD", "€": "EUR"}
_RESULT_NOUNS = r"(?:revenue|sales|profit|savings|in\s+savings|saved|pipeline|in\s+pipeline|roi|return)"
_COUNT_NOUNS = (
    r"(?:leads|enquiries|inquiries|clients|customers|bookings|orders|sign-?ups|conversions|"
    r"subscribers|downloads|installs|sales|demos|meetings)"
)
_WORD_MULT = {"doubled": "2", "tripled": "3", "triple": "3", "quadrupled": "4", "quadruple": "4"}

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # "£4.20 for every £1 spent" is a ROAS of 4.2 written as money (missed in the wild set, run 1).
    ("multiplier", re.compile(rf"[£$€]\s?(?P<n>{_NUM})\s+(?:back\s+)?for\s+every\s+[£$€]\s?1\b", re.I)),
    # "ROAS of 4.2", "4.2 ROAS", "4.2x ROAS": a ROAS is a multiplier whatever its spelling.
    ("multiplier", re.compile(rf"\bROAS\s+(?:of\s+)?(?P<n>{_NUM})\s?[x×]?(?![\w%])", re.I)),
    ("multiplier", re.compile(rf"(?<![\w.,])(?P<n>{_NUM})\s?[x×]?\s+ROAS\b", re.I)),
    ("percent", re.compile(rf"(?<![\w.,])[+\-]?(?P<n>{_NUM})\s?(?:%|per\s?cent\b|percent\b)", re.I)),
    ("multiplier", re.compile(rf"(?<![\w.,])(?P<n>{_NUM})\s?(?:[x×](?![\w\d])|times\b)", re.I)),
    # "triple" without the -d too ("viewings roughly triple"); bare "double" is left out on purpose,
    # because "double counting" is the most common phrase in tracking work and is not a result.
    ("multiplier", re.compile(r"\b(?P<w>doubled|tripled|triple|quadrupled|quadruple)\b", re.I)),
    (
        "money",
        re.compile(
            # "]?" lets "[£240k] in pipeline" through: drafts with template brackets left in (wild set).
            rf"(?P<c>[£$€])\s?(?P<n>{_NUM})\s?(?P<u>[km]\b|bn\b|million\b|thousand\b)?\]?"
            rf"(?=\s+(?:of\s+|in\s+)?(?:extra\s+|additional\s+|new\s+|more\s+|annual\s+|monthly\s+)?{_RESULT_NOUNS}\b)",
            re.I,
        ),
    ),
    (
        "money",
        re.compile(
            rf"\b(?:saved|generated|added|drove|delivered|unlocked)\s+(?:them\s+|clients?\s+|over\s+|more\s+than\s+)?"
            rf"(?P<c>[£$€])\s?(?P<n>{_NUM})\s?(?P<u>[km]\b|bn\b|million\b|thousand\b)?",
            re.I,
        ),
    ),
    (
        "count",
        re.compile(
            rf"(?<![\w.,£$€])(?P<n>{_NUM})\s?(?P<u>[k]\b)?\s+(?:more\s+|new\s+|extra\s+|additional\s+|qualified\s+)*"
            rf"(?P<noun>{_COUNT_NOUNS})\b",
            re.I,
        ),
    ),
]

_UNITS = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000, "bn": 1_000_000_000}


@dataclass(frozen=True)
class Claim:
    """One result claim found in text: where it is, what it says, and its comparison key."""

    start: int
    end: int
    text: str
    kind: str
    value: str
    context: frozenset[str]

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.value)


def _norm_number(raw: str, unit: str | None = None) -> str:
    try:
        n = Decimal(raw.replace(",", ""))
    except InvalidOperation:  # pragma: no cover - the regex only admits digits
        return raw
    if unit:
        n *= _UNITS[unit.lower()]
    return format(n.normalize(), "f")


def _context(text: str, start: int, end: int, window: int = 60) -> frozenset[str]:
    """Metric words near the claim, so a strict check can ask *what* the number measures."""
    # Stay inside the claim's own sentence: run 1 let a window cross into the next line of the facts
    # file, so "140% more enquiries" picked up "ROAS" from the line below and strict mode rejected it.
    left = max(text.rfind(c, 0, start) for c in ".!?\n;") + 1
    rights = [i for i in (text.find(c, end) for c in ".!?\n;") if i != -1]
    right = min(rights) if rights else len(text)
    near = text[max(left, start - window) : min(right, end + window)].lower()
    words = set(re.findall(r"[a-z][a-z\-]+", near))
    if "conversion rate" in near:
        words.add("conversion")
    return frozenset(words & METRIC_WORDS)


def _to_claim(text: str, kind: str, m: re.Match[str]) -> Claim:
    g = m.groupdict()
    value = _WORD_MULT[g["w"].lower()] if g.get("w") else _norm_number(g["n"], g.get("u"))
    if kind == "money":
        value = f"{_CURRENCY[g['c']]}:{value}"
    if kind == "count":
        value = f"{value}:{g['noun'].lower().replace('-', '').rstrip('s')}"
    return Claim(m.start(), m.end(), m.group(0), kind, value, _context(text, m.start(), m.end()))


def find_claims(text: str) -> list[Claim]:
    """Every result claim in ``text``, left to right, with overlapping matches removed."""
    found: list[Claim] = []
    for kind, rx in PATTERNS:
        found.extend(_to_claim(text, kind, m) for m in rx.finditer(text))
    found.sort(key=lambda c: (c.start, -(c.end - c.start)))
    kept: list[Claim] = []
    for c in found:
        if kept and c.start < kept[-1].end:
            continue  # "ROAS of 4.2x" also matches the bare "4.2x"; keep the longer, earlier one
        kept.append(c)
    return kept
