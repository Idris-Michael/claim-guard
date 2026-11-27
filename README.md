# claim-guard

Stops AI-written sales copy from citing results nobody verified.

A model asked to write a persuasive pitch will happily write "clients typically see a 340% lift".
claim-guard finds every result-style claim in a draft (percentages, multipliers, ROAS, money
results, counts like "320 new leads"), checks each one against a file of verified results, and
replaces the ones it can't back with `[PROOF POINT: verified metric required]`. Prices, dates and
team sizes are not results and are left alone. No model calls: it is plain Python with no
dependencies, and it scores a pitch in about 0.24 ms.

![claim-guard removing an invented 340% and, in strict mode, a verified 40% used for the wrong metric](docs/demo.gif)

## Results

300 cold emails written by Claude Haiku 5.5. Each one had to include a fixed recipe of planted
phrases, so the right answer for every phrase is known: verified results to keep, fakes to remove,
and prices or dates to leave untouched. Pitches 0–199 were used while building; 200–299 were
generated after the last change and scored once.

**Held-out set (100 emails, 583 planted phrases):**

| guard | verified kept | near misses removed | invented removed | metric swaps removed | prices/dates untouched |
|---|---|---|---|---|---|
| substring check (the guard this replaces) | 126/154 | 78/100 | 56/99 | 0/42 | 188/188 |
| claim-guard, value mode | **154/154** | **100/100** | **99/99** | 0/42 | 188/188 |
| claim-guard, `--strict` | **154/154** | **100/100** | **99/99** | **35/42** | 188/188 |

The development set (200 emails) gives the same picture; see `bench/results.json`.

- **Near miss**: a verified number nudged, such as 27% → 7% or 4.2 → 2.4. The old guard accepted a
  claim if its text appeared anywhere in the verified file, so "7%" passed because "27%" was there.
  claim-guard compares parsed values, not text.
- **Metric swap**: a verified number used for something else, such as "40% more sales" when the
  verified 40% was a fall in cost per lead. Value mode can't see this; `--strict` also requires the
  sentence to be about the same metric. It still misses 7 of 42, mostly sentences that mention both
  metrics at once ("traffic doubled and bookings…").
- **Wording I didn't choose.** The planted phrases are my wording, so I also asked Haiku for 30
  emails with its own invented numbers. It mostly refused and left `[X]%` placeholders; four emails
  had 11 concrete claims. Run 1 caught 8. The three misses ("roughly triple", "£4.20 for every £1",
  "[£240k] in pipeline") are now covered and tested, but that 11/11 was fixed on the same set and is
  not a held-out score. Details: [`bench/wild_review.md`](bench/wild_review.md).

## What broke while building it

Run 1 of strict mode wrongly removed 46 verified claims. The context window around each claim ran
past the end of its line in the facts file, so "140% more enquiries" picked up "ROAS" from the line
below and looked like a different metric. Context now stops at the sentence boundary, and
"enquiries" and "demos" were added as metric words. Run 1's output is kept in
`bench/results_run1.json`; the held-out set was generated after this fix.

## Use it

```bash
uv sync
uv run claim-guard draft.txt --facts verified.md            # exit 1 if anything was removed
uv run claim-guard draft.txt --facts verified.md --strict
```

```python
from claim_guard import VerifiedSource, guard

facts = VerifiedSource(open("verified.md").read())  # parse once, reuse per draft
result = guard(model_output, facts, mode="strict")
send(result.text) if not result.removed else ask_a_person(result)
```

A missing or unreadable facts file removes every claim (fail closed). The exit code lets it gate a
pipeline step or a pre-send hook.

## Reproduce

```bash
uv run pytest                                   # 40 tests, 100% coverage
uv run python bench/run.py --ids 200-299 --out results_heldout.json
uv run python bench/make_pitches.py --n 300     # regenerates pitches with the claude CLI (subscription)
```

## Limits

- English, and £ $ € only. Claims written out in words ("forty per cent") are not detected.
- Strict mode judges "same metric" from a fixed word list in the claim's sentence. A verified fact
  with no metric word, or a sentence naming two metrics, can let a swap through.
- It checks that a number was verified, not that the sentence around it is honest ("up to 40%").

## Where it came from

A TypeScript version guards outbound pitches in my agency's operator hub. This is a clean Python
rewrite with the substring bug fixed and a benchmark the original never had. MIT licence.
