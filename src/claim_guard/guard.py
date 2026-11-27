"""Check claims in a draft against a verified source and replace the ones that aren't backed.

Two modes:

* ``value`` (default): a claim passes when the verified source states the same kind of result with
  the same value. "40%" no longer passes just because "140%" is verified, which is how the
  substring check this replaces failed.
* ``strict``: the value must also be about the same thing. "40% lower cost per lead" does not make
  "40% more sales" true. Stricter, so it also catches more honest rewordings; the benchmark
  reports both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from claim_guard.claims import Claim, find_claims

PLACEHOLDER = "[PROOF POINT: verified metric required]"
Mode = Literal["value", "strict"]


@dataclass(frozen=True)
class Finding:
    claim: Claim
    verified: bool
    reason: str


@dataclass(frozen=True)
class GuardResult:
    text: str
    findings: tuple[Finding, ...]

    @property
    def removed(self) -> list[str]:
        return [f.claim.text for f in self.findings if not f.verified]


class VerifiedSource:
    """The facts a draft may cite, reduced to claim keys once so every check is a lookup."""

    def __init__(self, text: str) -> None:
        self.claims = find_claims(text)
        self._by_key: dict[tuple[str, str], list[Claim]] = {}
        for c in self.claims:
            self._by_key.setdefault(c.key, []).append(c)

    def check(self, claim: Claim, mode: Mode) -> Finding:
        matches = self._by_key.get(claim.key, [])
        if not matches:
            return Finding(claim, False, "no verified fact states this value")
        if mode == "value":
            return Finding(claim, True, "value matches a verified fact")
        for fact in matches:
            # A fact with no metric word, or a draft sentence with none, cannot conflict.
            if not fact.context or not claim.context or fact.context & claim.context:
                return Finding(claim, True, "value and metric match a verified fact")
        return Finding(claim, False, "value is verified, but for a different metric")


_RUN = re.compile(rf"(?:{re.escape(PLACEHOLDER)}[\s,/&+]*){{2,}}")


def guard(draft: str, source: VerifiedSource | str, mode: Mode = "value") -> GuardResult:
    """Return ``draft`` with every unverified claim replaced by :data:`PLACEHOLDER`."""
    src = source if isinstance(source, VerifiedSource) else VerifiedSource(source)
    findings = tuple(src.check(c, mode) for c in find_claims(draft))
    out = []
    pos = 0
    for f in findings:
        if f.verified:
            continue
        out.append(draft[pos : f.claim.start])
        out.append(PLACEHOLDER)
        pos = f.claim.end
    out.append(draft[pos:])
    text = _RUN.sub(PLACEHOLDER + " ", "".join(out))
    return GuardResult(text, findings)
