"""Score three guards on the 200 model-written pitches.

* baseline  the substring guard this project replaces (src/claim_guard/baseline.py)
* value     claim_guard, values must match a verified fact exactly
* strict    claim_guard, the metric must match too

For every planted phrase the model actually wrote verbatim, a guard is right when it removes a
fake (near_miss, invented, metric_swap) and keeps a verified claim or a safe detail intact.
Writes bench/results.json and prints the table used in the README.

    uv run python bench/run.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "src"))

from claim_guard import VerifiedSource, find_claims, guard  # noqa: E402
from claim_guard.baseline import baseline_guard  # noqa: E402

SHOULD_REMOVE = {"near_miss", "invented", "metric_swap"}
CATEGORIES = ["verified", "near_miss", "invented", "metric_swap", "safe"]


def run_guards(text: str, facts: str, src: VerifiedSource) -> dict[str, str]:
    return {
        "baseline": baseline_guard(text, facts)[0],
        "value": guard(text, src, "value").text,
        "strict": guard(text, src, "strict").text,
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="0-199", help="pitch id range, e.g. 0-199 (dev) or 200-299 (held out)")
    ap.add_argument("--out", default="results.json")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.ids.split("-"))
    facts = (HERE / "facts.md").read_text(encoding="utf-8")
    src = VerifiedSource(facts)
    rows = [json.loads(x) for x in (HERE / "pitches.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = sorted((r for r in rows if lo <= r["id"] <= hi), key=lambda r: r["id"])

    right: dict[str, Counter[str]] = defaultdict(Counter)
    seen: Counter[str] = Counter()
    missing = 0
    unplanted: list[str] = []
    errors: list[dict[str, object]] = []
    timings: list[float] = []

    for row in rows:
        text = row["text"]
        t0 = time.perf_counter()
        outs = run_guards(text, facts, src)
        timings.append((time.perf_counter() - t0) / 3)
        spans = []
        for p in row["plants"]:
            phrase, cat = p["phrase"], p["category"]
            at = text.find(phrase)
            if at < 0:
                missing += 1  # the model reworded it; no label, so it is not scored
                continue
            spans.append((at, at + len(phrase)))
            seen[cat] += 1
            for name, out in outs.items():
                removed = phrase not in out
                ok = removed if cat in SHOULD_REMOVE else not removed
                right[name][cat] += ok
                if not ok:
                    errors.append({"pitch": row["id"], "guard": name, "category": cat, "phrase": phrase})
        for c in find_claims(text):
            if not any(s <= c.start < e for s, e in spans):
                unplanted.append(c.text)

    table = {
        name: {cat: {"right": right[name][cat], "of": seen[cat]} for cat in CATEGORIES}
        for name in ("baseline", "value", "strict")
    }
    timings.sort()
    result = {
        "ids": a.ids,
        "pitches": len(rows),
        "model": rows[0]["model"] if rows else None,
        "planted_scored": sum(seen.values()),
        "planted_reworded_not_scored": missing,
        "unplanted_claims_model_added": len(unplanted),
        "unplanted_examples": unplanted[:15],
        "median_ms_per_pitch": round(timings[len(timings) // 2] * 1000, 3) if timings else None,
        "results": table,
        "errors": errors,
    }
    (HERE / a.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8")

    print(f"{len(rows)} pitches, {sum(seen.values())} planted phrases scored, {missing} reworded (unscored)")
    print("| guard | " + " | ".join(CATEGORIES) + " |")
    print("|---|" + "---|" * len(CATEGORIES))
    for name, cats in table.items():
        cells = [f"{v['right']}/{v['of']}" for v in cats.values()]
        print(f"| {name} | " + " | ".join(cells) + " |")
    print(f"unplanted claims the model added anyway: {len(unplanted)}")


if __name__ == "__main__":
    main()
