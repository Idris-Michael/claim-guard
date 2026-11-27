"""claim-guard DRAFT --facts FACTS [--strict]: print the guarded draft, list what was removed.

Exit code 1 when anything was removed, so the check can gate a pipeline or a pre-send hook.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from claim_guard.guard import guard


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="claim-guard", description=__doc__)
    p.add_argument("draft", type=Path, help="draft text file, or - for stdin")
    p.add_argument("--facts", type=Path, required=True, help="verified facts the draft may cite")
    p.add_argument("--strict", action="store_true", help="also require the metric to match")
    a = p.parse_args(argv)

    draft = sys.stdin.read() if str(a.draft) == "-" else a.draft.read_text(encoding="utf-8")
    try:
        facts = a.facts.read_text(encoding="utf-8")
    except OSError as e:
        # Fail closed: with no verified source, nothing can be cited.
        print(f"claim-guard: cannot read facts ({e}); every claim will be removed", file=sys.stderr)
        facts = ""
    r = guard(draft, facts, "strict" if a.strict else "value")
    print(r.text)
    for f in r.findings:
        mark = "kept   " if f.verified else "REMOVED"
        print(f"{mark} {f.claim.text!r:32} {f.reason}", file=sys.stderr)
    return 1 if r.removed else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
