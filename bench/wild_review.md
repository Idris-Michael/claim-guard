# Wild set: hand review

30 cold emails written by Claude Haiku 5.5 with no planted claims and no facts file, asked for
"specific results ... concrete numbers, percentages, money and multipliers, in varied wording"
(`bench/make_wild.py`, output in `bench/wild.jsonl`). Every result here is invented, so every one
should be removed. I read all 30.

**First finding: the model mostly refused to invent numbers.** 26 of 30 emails used template
placeholders such as `[X]%` or `£[amount]` instead. Only four (ids 9, 16, 17, 25) state concrete
results.

| id | result claims in the text | run 1 (as shipped in the planted benchmark) | after fix |
|---|---|---|---|
| 9 | "38%", "viewings roughly **triple**" | 38% caught; "triple" missed (only "tripled" was known) | both caught |
| 16 | "38%", "nearly doubled", "returned **£4.20 for every £1** spent" | 38%, doubled caught; the ROAS-as-money ratio missed | all caught |
| 17 | "[61%]", "[8%]", "[13%]", "**[£240k]** in pipeline", "[2.6x]" | percentages and 2.6x caught; "[£240k]" missed (the bracket broke the pattern) | all caught |
| 25 | "roughly tripled" | caught | caught |

Run 1: **8 of 11** concrete claims caught. After three pattern fixes: **11 of 11**.

The fixes were made on this same set, so 11/11 is not a held-out score; it says these three
wordings are now covered and pinned by tests in `tests/test_claims.py`. Not counted as a claim:
"we moved [£30k] a month of ad spend" in id 17 (an action, not a result) and call lengths such as
"a 20-minute call". Bare "double" stays out on purpose: "double counting" is the most common
phrase in tracking work and is not a result.

Rerunning the planted benchmark after these fixes changed no number in either table.
