"""Have Claude Haiku write 200 cold pitches, each containing its planted claims word for word.

The model writes the prose so the guard is tested on real model output, not on sentences I wrote.
Output: bench/pitches.jsonl (committed, so run.py needs no model). Uses the `claude` CLI on a
subscription with tools disabled; costs nothing per call.

    uv run python bench/make_pitches.py --n 200 --workers 4
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from plant import as_dicts, recipe

HERE = Path(__file__).parent
OUT = HERE / "pitches.jsonl"
MODEL = "claude-haiku-5-5"
SECTORS = [
    "a dental group",
    "an outdoor-gear shop",
    "a law firm",
    "a day spa",
    "a bike retailer",
    "a recruitment agency",
    "a kitchen fitter",
    "a B2B software startup",
    "a pet-supplies brand",
    "an estate agent",
]
SYSTEM = "You write short, plain cold emails for a small UK analytics agency. Output only the email body."


def prompt(i: int, phrases: list[str]) -> str:
    listed = "\n".join(f"- {p}" for p in phrases)
    return (
        f"Write a cold email (90 to 140 words) to the marketing lead at {SECTORS[i % len(SECTORS)]}. "
        "Present the results below as things the agency achieved for past clients, and the other "
        "phrases as details about the agency. Include every phrase below exactly as written, character "
        "for character. Do not add any other numbers.\n\n" + listed
    )


def write_one(cli: str, i: int) -> dict[str, object]:
    plants = recipe(i)
    args = [cli, "-p", "--model", MODEL, "--output-format", "text", "--tools", "", "--strict-mcp-config"]
    args += ["--disable-slash-commands", "--setting-sources", "", "--no-session-persistence"]
    args += ["--system-prompt", SYSTEM]
    proc = subprocess.run(  # noqa: S603 - argv list, binary resolved from PATH
        args,
        input=prompt(i, [p.phrase for p in plants]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pitch {i}: claude exited {proc.returncode}: {proc.stderr[:200]}")
    return {"id": i, "model": MODEL, "plants": as_dicts(plants), "text": proc.stdout.strip()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    cli = shutil.which("claude")
    if not cli:
        raise SystemExit("claude CLI not on PATH")
    done = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            done[row["id"]] = row
    todo = [i for i in range(a.n) if i not in done]
    print(f"{len(done)} cached, {len(todo)} to write")
    with ThreadPoolExecutor(a.workers) as pool:
        for row in pool.map(lambda i: write_one(cli, i), todo):
            done[row["id"]] = row  # type: ignore[index]
            with OUT.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"pitch {row['id']} written", flush=True)


if __name__ == "__main__":
    main()
