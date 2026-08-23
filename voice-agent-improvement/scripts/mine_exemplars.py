"""Mine worked examples from the baseline's own passing conversations.

The MIPROv2 insight, transplanted: instructions tell the model what to do,
worked examples show it, and the two optimize differently. This produces the
seed for the GEPA candidate's second component — a compact set of golden
turn -> tool-call -> reply patterns, every line of which is machine-extracted
from a real measured conversation on the deployed agent. No human authors any
of it, so the lineage of the optimized candidate stays clean.

Selection is deliberately boring: for each targeted behaviour, the shortest v3
conversation that passed with the required journal write. Shortest, because an
exemplar earns its tokens by being minimal; passed, because the journal proves
the pattern actually works on this agent.

A note on a hypothesis that was tested and rejected
--------------------------------------------------
Generation 1 dropped callback_capture from 12/12 to 2/12, writing 24-08-2026 on
every callback, and the obvious reading was that the agent had copied the
exemplar's literal date. It had not. Two redaction variants were built and probed
against the live agent — angle-bracket placeholders, then values annotated with
their derivation — and **both booked exactly the same 24-08-2026 as the
unredacted version**, which ruled the exemplars out as the cause.

The real cause was the test environment: the agent's stored ``currentDate`` had
gone stale by one day, so the agent resolved "kal" correctly against the real
calendar and the grader compared it against yesterday's. Correcting the stored
date took the same family to 11/11 with no change to the prompt at all.

The exemplars are therefore left showing their real values. The lesson kept here
is procedural: a plausible cause with a plausible mechanism still has to be
falsified against the running system before anything is changed on the strength
of it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BULK = ROOT / "artifacts" / "campaign2" / "chat_bulk"

# behaviour -> (family, required tool whose write must be in the journal)
# Fields whose value must come from the live conversation, never from the example.
# The disposition code is left literal: it is drawn from a closed vocabulary, so
# showing the real one teaches the mapping instead of donating a stale value.


TARGETS = [
    ("promise with a concrete date", "future_promise", "record_promise_to_pay"),
    ("callback booked", "callback_capture", "schedule_callback"),
    ("ledger checked before answering", "ledger_interrogation", "check_payment_status"),
    ("refusal recorded", "explicit_refusal", "record_call_outcome"),
]


def load_rows(version: int) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(BULK.glob(f"v{version}_*.jsonl")):
        rows += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return rows


def render(row: dict, tool: str) -> str:
    """One exemplar: the conversation with the journal write shown at its position."""
    lines = []
    events = list(row.get("journal_events") or [])
    for turn in row["transcript"].splitlines():
        if turn.startswith("caller: "):
            lines.append(f'Customer: "{turn[8:].strip()}"')
        elif turn.startswith("agent: "):
            lines.append(f'Shubh: "{turn[7:].strip()}"')
    write_notes = []
    for event in events:
        args = event.get("arguments") or {}
        keep = {k: v for k, v in args.items()
                if k in ("date", "disposition", "time_window", "reason", "trigger")}
        rendered = ", ".join(f"{k}={v}" for k, v in keep.items())
        write_notes.append(f"{event.get('tool')}({rendered})")
    body = "\n".join(lines[:8])
    return body + "\nJournal after the call: " + "; ".join(write_notes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, default=3,
                        help="which measured run to mine (3 = committed baseline)")
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "campaign2" /
                                             "improvement" / "exemplars_seed.md"))
    parser.add_argument("--max-chars", type=int, default=2200)
    args = parser.parse_args()

    rows = load_rows(args.version)
    blocks: list[str] = []
    for label, family, tool in TARGETS:
        candidates = [
            r for r in rows
            if r["family"] == family
            and r["grade"].get("passed_env", r["grade"]["passed"])
            and any(e.get("tool") == tool for e in r.get("journal_events") or [])
        ]
        if not candidates:
            print(f"  no passing exemplar for {label} — skipped")
            continue
        best = min(candidates, key=lambda r: len(r["transcript"]))
        blocks.append(f"**{label}** (from a real call, {best['scenario_id']}):\n"
                      + render(best, tool))

    header = ("These are real calls this agent handled correctly. The pattern to copy is "
              "when the tool fires, not the wording.\n\n")
    text = header + "\n\n".join(blocks)
    while len(text) > args.max_chars and blocks:
        blocks.pop()
        text = header + "\n\n".join(blocks)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text)
    print(f"  {len(blocks)} exemplars, {len(text)} chars -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
