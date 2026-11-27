"""30 pitches where the model invents its own numbers, to test the extractor on wording I didn't choose.

Every number in these is invented (the facts file is not shown to the model), so every result claim
should be removed. bench/wild_review.md records a hand read of all 30 for claims the extractor missed.

    uv run python bench/make_wild.py
"""

from __future__ import annotations

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from make_pitches import MODEL, SECTORS, SYSTEM
from make_pitches import subprocess as sp

OUT = Path(__file__).parent / "wild.jsonl"
PROMPT = (
    "Write a persuasive cold email (90 to 140 words) to the marketing lead at {sector}. Make it "
    "convincing with specific results the agency has achieved for similar clients: use concrete "
    "numbers, percentages, money and multipliers, in varied wording."
)


def one(cli: str, i: int) -> dict[str, object]:
    args = [cli, "-p", "--model", MODEL, "--output-format", "text", "--tools", "", "--strict-mcp-config"]
    args += ["--disable-slash-commands", "--setting-sources", "", "--no-session-persistence"]
    args += ["--system-prompt", SYSTEM]
    p = sp.run(
        args,
        input=PROMPT.format(sector=SECTORS[i % len(SECTORS)]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        check=True,
    )
    return {"id": i, "model": MODEL, "text": p.stdout.strip()}


def main() -> None:
    cli = shutil.which("claude")
    if not cli:
        raise SystemExit("claude CLI not on PATH")
    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(lambda i: one(cli, i), range(30)))
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    print(f"wrote {len(rows)} wild pitches")


if __name__ == "__main__":
    main()
